#include <stdio.h>
#include <signal.h>
#include <cassert>

#ifdef QCOM
#include "cameras/camera_qcom.h"
#else
#include "cameras/camera_frame_stream.h"
#endif

#include "common/util.h"
#include "common/swaglog.h"

#include "common/visionipc.h"
#include "common/visionbuf.h"
#include "common/visionimg.h"

#include "messaging.hpp"

#include "transforms/rgb_to_yuv.h"

#include "clutil.h"
#include "bufs.h"

#include <libyuv.h>
#include <czmq.h>
#include <capnp/serialize.h>
#include <jpeglib.h>
#include "cereal/gen/cpp/log.capnp.h"

#define UI_BUF_COUNT 4
#define YUV_COUNT 40
#define MAX_CLIENTS 5

extern "C" {
volatile sig_atomic_t do_exit = 0;
}

void set_do_exit(int sig) {
  do_exit = 1;
}

struct VisionState;

struct VisionClientState {
  VisionState *s;
  int fd;
  pthread_t thread_handle;
  bool running;
};

struct VisionClientStreamState {
  bool subscribed;
  int bufs_outstanding;
  bool tb;
  TBuffer* tbuffer;
  PoolQueue* queue;
};

struct VisionState {
  int frame_width, frame_height;
  int frame_stride;
  int frame_size;

  int ion_fd;

  // cl state
  cl_device_id device_id;
  cl_context context;

  cl_program prg_debayer_rear;
  cl_program prg_debayer_front;
  cl_kernel krnl_debayer_rear;
  cl_kernel krnl_debayer_front;

  // processing
  TBuffer ui_tb;
  TBuffer ui_front_tb;

  mat3 yuv_transform;
  TBuffer *yuv_tb;
  TBuffer *yuv_front_tb;

  // TODO: refactor for both cameras?
  Pool yuv_pool;
  VisionBuf yuv_ion[YUV_COUNT];
  cl_mem yuv_cl[YUV_COUNT];
  YUVBuf yuv_bufs[YUV_COUNT];
  FrameMetadata yuv_metas[YUV_COUNT];
  size_t yuv_buf_size;
  int yuv_width, yuv_height;
  RGBToYUVState rgb_to_yuv_state;

  // for front camera recording
  Pool yuv_front_pool;
  VisionBuf yuv_front_ion[YUV_COUNT];
  cl_mem yuv_front_cl[YUV_COUNT];
  YUVBuf yuv_front_bufs[YUV_COUNT];
  FrameMetadata yuv_front_metas[YUV_COUNT];
  size_t yuv_front_buf_size;
  int yuv_front_width, yuv_front_height;
  RGBToYUVState front_rgb_to_yuv_state;

  size_t rgb_buf_size;
  int rgb_width, rgb_height, rgb_stride;
  VisionBuf rgb_bufs[UI_BUF_COUNT];
  cl_mem rgb_bufs_cl[UI_BUF_COUNT];

  size_t rgb_front_buf_size;
  int rgb_front_width, rgb_front_height, rgb_front_stride;
  VisionBuf rgb_front_bufs[UI_BUF_COUNT];
  cl_mem rgb_front_bufs_cl[UI_BUF_COUNT];
  int front_meteringbox_xmin, front_meteringbox_xmax;
  int front_meteringbox_ymin, front_meteringbox_ymax;


  cl_mem camera_bufs_cl[FRAME_BUF_COUNT];
  VisionBuf camera_bufs[FRAME_BUF_COUNT];
  VisionBuf focus_bufs[FRAME_BUF_COUNT];
  VisionBuf stats_bufs[FRAME_BUF_COUNT];

  cl_mem front_camera_bufs_cl[FRAME_BUF_COUNT];
  VisionBuf front_camera_bufs[FRAME_BUF_COUNT];

  DualCameraState cameras;

  zsock_t *terminate_pub;

  Context * msg_context;
  PubSocket *frame_sock;
  PubSocket *front_frame_sock;
  PubSocket *thumbnail_sock;

  pthread_mutex_t clients_lock;
  VisionClientState clients[MAX_CLIENTS];
};

// frontview thread
void* frontview_thread(void *arg) {
  int err;
  VisionState *s = (VisionState*)arg;

  set_thread_name("frontview");

  s->msg_context = Context::create();

  // we subscribe to this for placement of the AE metering box
  // TODO: the loop is bad, ideally models shouldn't affect sensors
  Context *msg_context = Context::create();
  SubSocket *monitoring_sock = SubSocket::create(msg_context, "driverState", "127.0.0.1", true);
  assert(monitoring_sock != NULL);

  cl_command_queue q = clCreateCommandQueue(s->context, s->device_id, 0, &err);
  assert(err == 0);

  for (int cnt = 0; !do_exit; cnt++) {
    int buf_idx = tbuffer_acquire(&s->cameras.front.camera_tb);
    if (buf_idx < 0) {
      break;
    }

    int ui_idx = tbuffer_select(&s->ui_front_tb);
    FrameMetadata frame_data = s->cameras.front.camera_bufs_metadata[buf_idx];

    double t1 = millis_since_boot();

    err = clSetKernelArg(s->krnl_debayer_front, 0, sizeof(cl_mem), &s->front_camera_bufs_cl[buf_idx]);
    assert(err == 0);
    err = clSetKernelArg(s->krnl_debayer_front, 1, sizeof(cl_mem), &s->rgb_front_bufs_cl[ui_idx]);
    assert(err == 0);
    float digital_gain = 1.0;
    err = clSetKernelArg(s->krnl_debayer_front, 2, sizeof(float), &digital_gain);
    assert(err == 0);

    cl_event debayer_event;
    const size_t debayer_work_size = s->rgb_front_height;
    const size_t debayer_local_work_size = 128;
    err = clEnqueueNDRangeKernel(q, s->krnl_debayer_front, 1, NULL,
                                 &debayer_work_size, &debayer_local_work_size, 0, 0, &debayer_event);
    assert(err == 0);
    clWaitForEvents(1, &debayer_event);
    clReleaseEvent(debayer_event);

    tbuffer_release(&s->cameras.front.camera_tb, buf_idx);

    visionbuf_sync(&s->rgb_front_bufs[ui_idx], VISIONBUF_SYNC_FROM_DEVICE);

    // set front camera metering target
    Message *msg = monitoring_sock->receive(true);
    if (msg != NULL) {
      auto amsg = kj::heapArray<capnp::word>((msg->getSize() / sizeof(capnp::word)) + 1);
      memcpy(amsg.begin(), msg->getData(), msg->getSize());

      capnp::FlatArrayMessageReader cmsg(amsg);
      cereal::Event::Reader event = cmsg.getRoot<cereal::Event>();

      float face_prob = event.getDriverState().getFaceProb();
      float face_position[2];
      face_position[0] = event.getDriverState().getFacePosition()[0];
      face_position[1] = event.getDriverState().getFacePosition()[1];

      // set front camera metering target
      if (face_prob > 0.4)
      {
        int x_offset = s->rgb_front_width - 0.5 * s->rgb_front_height;
        s->front_meteringbox_xmin = x_offset + (face_position[0] + 0.5) * (0.5 * s->rgb_front_height) - 72;
        s->front_meteringbox_xmax = x_offset + (face_position[0] + 0.5) * (0.5 * s->rgb_front_height) + 72;
        s->front_meteringbox_ymin = (face_position[1] + 0.5) * (s->rgb_front_height) - 72;
        s->front_meteringbox_ymax = (face_position[1] + 0.5) * (s->rgb_front_height) + 72;
      }
      else // use default setting if no face
      {
        s->front_meteringbox_ymin = s->rgb_front_height * 1 / 3;
        s->front_meteringbox_ymax = s->rgb_front_height * 1;
        s->front_meteringbox_xmin = s->rgb_front_width * 3 / 5;
        s->front_meteringbox_xmax = s->rgb_front_width;
      }

      delete msg;
    }

    // auto exposure
    const uint8_t *bgr_front_ptr = (const uint8_t*)s->rgb_front_bufs[ui_idx].addr;
#ifndef DEBUG_DRIVER_MONITOR
    if (cnt % 3 == 0)
#endif
    {
      // use driver face crop for AE
      int x_start;
      int x_end;
      int y_start;
      int y_end;

      if (s->front_meteringbox_xmax > 0)
      {
        x_start = s->front_meteringbox_xmin<0 ? 0:s->front_meteringbox_xmin;
        x_end = s->front_meteringbox_xmax>=s->rgb_front_width ? s->rgb_front_width-1:s->front_meteringbox_xmax;
        y_start = s->front_meteringbox_ymin<0 ? 0:s->front_meteringbox_ymin;
        y_end = s->front_meteringbox_ymax>=s->rgb_front_height ? s->rgb_front_height-1:s->front_meteringbox_ymax;
      }
      else
      {
        y_start = s->rgb_front_height * 1 / 3;
        y_end = s->rgb_front_height * 1;
        x_start = s->rgb_front_width * 3 / 5;
        x_end = s->rgb_front_width;
      }

      uint32_t lum_binning[256] = {0,};
      for (int y = y_start; y < y_end; ++y) {
        for (int x = x_start; x < x_end; x += 2) { // every 2nd col
          const uint8_t *pix = &bgr_front_ptr[y * s->rgb_front_stride + x * 3];
          unsigned int lum = (unsigned int)pix[0] + pix[1] + pix[2];
#ifdef DEBUG_DRIVER_MONITOR
          uint8_t *pix_rw = (uint8_t *)pix;

          // set all the autoexposure pixels to pure green (pixel format is bgr)
          pix_rw[0] = pix_rw[2] = 0;
          pix_rw[1] = 0xff;
#endif
          lum_binning[std::min(lum / 3, 255u)]++;
        }
      }
      const unsigned int lum_total = (y_end - y_start) * (x_end - x_start)/2;
      unsigned int lum_cur = 0;
      int lum_med = 0;
      for (lum_med=0; lum_med<256; lum_med++) {
        lum_cur += lum_binning[lum_med];
        if (lum_cur >= lum_total / 2) {
          break;
        }
      }
      camera_autoexposure(&s->cameras.front, lum_med / 256.0);
    }

    // push YUV buffer
    int yuv_idx = pool_select(&s->yuv_front_pool);
    s->yuv_front_metas[yuv_idx] = frame_data;

    rgb_to_yuv_queue(&s->front_rgb_to_yuv_state, q, s->rgb_front_bufs_cl[ui_idx], s->yuv_front_cl[yuv_idx]);
    visionbuf_sync(&s->yuv_front_ion[yuv_idx], VISIONBUF_SYNC_FROM_DEVICE);
    s->yuv_front_metas[yuv_idx] = frame_data;

    // no reference required cause we don't use this in visiond
    //pool_acquire(&s->yuv_front_pool, yuv_idx);
    pool_push(&s->yuv_front_pool, yuv_idx);
    //pool_release(&s->yuv_front_pool, yuv_idx);

    // send frame event
    {
      capnp::MallocMessageBuilder msg;
      cereal::Event::Builder event = msg.initRoot<cereal::Event>();
      event.setLogMonoTime(nanos_since_boot());

      auto framed = event.initFrontFrame();
      framed.setFrameId(frame_data.frame_id);
      framed.setEncodeId(cnt);
      framed.setTimestampEof(frame_data.timestamp_eof);
      framed.setFrameLength(frame_data.frame_length);
      framed.setIntegLines(frame_data.integ_lines);
      framed.setGlobalGain(frame_data.global_gain);
      framed.setLensPos(frame_data.lens_pos);
      framed.setLensSag(frame_data.lens_sag);
      framed.setLensErr(frame_data.lens_err);
      framed.setLensTruePos(frame_data.lens_true_pos);
      framed.setGainFrac(frame_data.gain_frac);
      framed.setFrameType(cereal::FrameData::FrameType::FRONT);

      auto words = capnp::messageToFlatArray(msg);
      auto bytes = words.asBytes();
      s->front_frame_sock->send((char*)bytes.begin(), bytes.size());
    }

    /*FILE *f = fopen("/tmp/test2", "wb");
    printf("%d %d\n", s->rgb_front_height, s->rgb_front_stride);
    fwrite(bgr_front_ptr, 1, s->rgb_front_stride * s->rgb_front_height, f);
    fclose(f);*/

    tbuffer_dispatch(&s->ui_front_tb, ui_idx);

    double t2 = millis_since_boot();

    //LOGD("front process: %.2fms", t2-t1);
  }

  delete monitoring_sock;

  return NULL;
}
// processing
void* processing_thread(void *arg) {
  int err;
  VisionState *s = (VisionState*)arg;

  set_thread_name("processing");

  err = set_realtime_priority(1);
  LOG("setpriority returns %d", err);

  // init cl stuff
  const cl_queue_properties props[] = {0}; //CL_QUEUE_PRIORITY_KHR, CL_QUEUE_PRIORITY_HIGH_KHR, 0};
  cl_command_queue q = clCreateCommandQueueWithProperties(s->context, s->device_id, props, &err);
  assert(err == 0);

  // init the net
  LOG("processing start!");

  for (int cnt = 0; !do_exit; cnt++) {
    int buf_idx = tbuffer_acquire(&s->cameras.rear.camera_tb);
    // int buf_idx = camera_acquire_buffer(s);
    if (buf_idx < 0) {
      break;
    }

    double t1 = millis_since_boot();

    FrameMetadata frame_data = s->cameras.rear.camera_bufs_metadata[buf_idx];
    uint32_t frame_id = frame_data.frame_id;

    if (frame_id == -1) {
      LOGE("no frame data? wtf");
      tbuffer_release(&s->cameras.rear.camera_tb, buf_idx);
      continue;
    }

    int ui_idx = tbuffer_select(&s->ui_tb);
    int rgb_idx = ui_idx;

    cl_event debayer_event;
    if (s->cameras.rear.ci.bayer) {
      err = clSetKernelArg(s->krnl_debayer_rear, 0, sizeof(cl_mem), &s->camera_bufs_cl[buf_idx]);
      cl_check_error(err);
      err = clSetKernelArg(s->krnl_debayer_rear, 1, sizeof(cl_mem), &s->rgb_bufs_cl[rgb_idx]);
      cl_check_error(err);
      err = clSetKernelArg(s->krnl_debayer_rear, 2, sizeof(float), &s->cameras.rear.digital_gain);
      assert(err == 0);

      const size_t debayer_work_size = s->rgb_height; // doesn't divide evenly, is this okay?
      const size_t debayer_local_work_size = 128;
      err = clEnqueueNDRangeKernel(q, s->krnl_debayer_rear, 1, NULL,
                                   &debayer_work_size, &debayer_local_work_size, 0, 0, &debayer_event);
      assert(err == 0);
    } else {
      assert(s->rgb_buf_size >= s->frame_size);
      assert(s->rgb_stride == s->frame_stride);
      err = clEnqueueCopyBuffer(q, s->camera_bufs_cl[buf_idx], s->rgb_bufs_cl[rgb_idx],
                                0, 0, s->rgb_buf_size, 0, 0, &debayer_event);
      assert(err == 0);
    }

    clWaitForEvents(1, &debayer_event);
    clReleaseEvent(debayer_event);

    tbuffer_release(&s->cameras.rear.camera_tb, buf_idx);

    visionbuf_sync(&s->rgb_bufs[rgb_idx], VISIONBUF_SYNC_FROM_DEVICE);


    double t2 = millis_since_boot();

    uint8_t *bgr_ptr = (uint8_t*)s->rgb_bufs[rgb_idx].addr;

    double yt1 = millis_since_boot();

    int yuv_idx = pool_select(&s->yuv_pool);

    s->yuv_metas[yuv_idx] = frame_data;

    uint8_t* yuv_ptr_y = s->yuv_bufs[yuv_idx].y;
    uint8_t* yuv_ptr_u = s->yuv_bufs[yuv_idx].u;
    uint8_t* yuv_ptr_v = s->yuv_bufs[yuv_idx].v;
    cl_mem yuv_cl = s->yuv_cl[yuv_idx];
    rgb_to_yuv_queue(&s->rgb_to_yuv_state, q, s->rgb_bufs_cl[rgb_idx], yuv_cl);
    visionbuf_sync(&s->yuv_ion[yuv_idx], VISIONBUF_SYNC_FROM_DEVICE);

    double yt2 = millis_since_boot();

    // keep another reference around till were done processing
    pool_acquire(&s->yuv_pool, yuv_idx);
    pool_push(&s->yuv_pool, yuv_idx);

    // send frame event
    {
      capnp::MallocMessageBuilder msg;
      cereal::Event::Builder event = msg.initRoot<cereal::Event>();
      event.setLogMonoTime(nanos_since_boot());

      auto framed = event.initFrame();
      framed.setFrameId(frame_data.frame_id);
      framed.setEncodeId(cnt);
      framed.setTimestampEof(frame_data.timestamp_eof);
      framed.setFrameLength(frame_data.frame_length);
      framed.setIntegLines(frame_data.integ_lines);
      framed.setGlobalGain(frame_data.global_gain);
      framed.setLensPos(frame_data.lens_pos);
      framed.setLensSag(frame_data.lens_sag);
      framed.setLensErr(frame_data.lens_err);
      framed.setLensTruePos(frame_data.lens_true_pos);
      framed.setGainFrac(frame_data.gain_frac);
#ifdef QCOM
      kj::ArrayPtr<const int16_t> focus_vals(&s->cameras.rear.focus[0], NUM_FOCUS);
      kj::ArrayPtr<const uint8_t> focus_confs(&s->cameras.rear.confidence[0], NUM_FOCUS);
      framed.setFocusVal(focus_vals);
      framed.setFocusConf(focus_confs);
#endif

#ifndef QCOM
      framed.setImage(kj::arrayPtr((const uint8_t*)s->yuv_ion[yuv_idx].addr, s->yuv_buf_size));
#endif

      kj::ArrayPtr<const float> transform_vs(&s->yuv_transform.v[0], 9);
      framed.setTransform(transform_vs);

      if (s->frame_sock != NULL) {
        auto words = capnp::messageToFlatArray(msg);
        auto bytes = words.asBytes();
        s->frame_sock->send((char*)bytes.begin(), bytes.size());
      }
    }

    // one thumbnail per 5 seconds (instead of %5 == 0 posenet)
    if (cnt % 100 == 3) {
      uint8_t* thumbnail_buffer = NULL;
      uint64_t thumbnail_len = 0;

      unsigned char *row = (unsigned char *)malloc(s->rgb_width/4*3);

      struct jpeg_compress_struct cinfo;
      struct jpeg_error_mgr jerr;

      cinfo.err = jpeg_std_error(&jerr);
      jpeg_create_compress(&cinfo);
      jpeg_mem_dest(&cinfo, &thumbnail_buffer, &thumbnail_len);

      cinfo.image_width = s->rgb_width / 4;
      cinfo.image_height = s->rgb_height / 4;
      cinfo.input_components = 3;
      cinfo.in_color_space = JCS_RGB;

      jpeg_set_defaults(&cinfo);
      jpeg_set_quality(&cinfo, 50, true);
      jpeg_start_compress(&cinfo, true);

      JSAMPROW row_pointer[1];
      for (int i = 0; i < s->rgb_height - 4; i+=4) {
        for (int j = 0; j < s->rgb_width*3; j+=12) {
          for (int k = 0; k < 3; k++) {
            uint16_t dat = 0;
            dat += bgr_ptr[s->rgb_stride*i + j + k];
            dat += bgr_ptr[s->rgb_stride*i + j+3 + k];
            dat += bgr_ptr[s->rgb_stride*(i+1) + j + k];
            dat += bgr_ptr[s->rgb_stride*(i+1) + j+3 + k];
            dat += bgr_ptr[s->rgb_stride*(i+2) + j + k];
            dat += bgr_ptr[s->rgb_stride*(i+2) + j+3 + k];
            dat += bgr_ptr[s->rgb_stride*(i+3) + j + k];
            dat += bgr_ptr[s->rgb_stride*(i+3) + j+3 + k];

            row[(j/4) + (2-k)] = dat/8;
          }
        }
        row_pointer[0] = row;
        jpeg_write_scanlines(&cinfo, row_pointer, 1);
      }
      free(row);
      jpeg_finish_compress(&cinfo);

      capnp::MallocMessageBuilder msg;
      cereal::Event::Builder event = msg.initRoot<cereal::Event>();
      event.setLogMonoTime(nanos_since_boot());

      auto thumbnaild = event.initThumbnail();
      thumbnaild.setFrameId(frame_data.frame_id);
      thumbnaild.setTimestampEof(frame_data.timestamp_eof);
      thumbnaild.setThumbnail(kj::arrayPtr((const uint8_t*)thumbnail_buffer, thumbnail_len));

      auto words = capnp::messageToFlatArray(msg);
      auto bytes = words.asBytes();
      if (s->thumbnail_sock != NULL) {
        s->thumbnail_sock->send((char*)bytes.begin(), bytes.size());
      }

      free(thumbnail_buffer);
    }

    tbuffer_dispatch(&s->ui_tb, ui_idx);

    // auto exposure over big box
    const int exposure_x = 290;
    const int exposure_y = 282 + 40;
    const int exposure_height = 314;
    const int exposure_width = 560;
    if (cnt % 3 == 0) {
      // find median box luminance for AE
      uint32_t lum_binning[256] = {0,};
      for (int y=0; y<exposure_height; y++) {
        for (int x=0; x<exposure_width; x++) {
          uint8_t lum = yuv_ptr_y[((exposure_y+y)*s->yuv_width) + exposure_x + x];
          lum_binning[lum]++;
        }
      }
      const unsigned int lum_total = exposure_height * exposure_width;
      unsigned int lum_cur = 0;
      int lum_med = 0;
      for (lum_med=0; lum_med<256; lum_med++) {
        // shouldn't be any values less than 16 - yuv footroom
        lum_cur += lum_binning[lum_med];
        if (lum_cur >= lum_total / 2) {
          break;
        }
      }
      // double avg = (double)acc / (big_box_width * big_box_height) - 16;
      // printf("avg %d\n", lum_med);

      camera_autoexposure(&s->cameras.rear, lum_med / 256.0);
    }

    pool_release(&s->yuv_pool, yuv_idx);
    double t5 = millis_since_boot();
    LOGD("queued: %.2fms, yuv: %.2f, | processing: %.3fms", (t2-t1), (yt2-yt1), (t5-t1));
  }

  return NULL;
}

// visionserver
void* visionserver_client_thread(void* arg) {
  int err;
  VisionClientState *client = (VisionClientState*)arg;
  VisionState *s = client->s;
  int fd = client->fd;

  set_thread_name("clientthread");

  zsock_t *terminate = zsock_new_sub(">inproc://terminate", "");
  assert(terminate);
  void* terminate_raw = zsock_resolve(terminate);

  VisionClientStreamState streams[VISION_STREAM_MAX] = {{0}};

  LOGW("client start fd %d", fd);

  while (true) {
    zmq_pollitem_t polls[2+VISION_STREAM_MAX] = {{0}};
    polls[0].socket = terminate_raw;
    polls[0].events = ZMQ_POLLIN;
    polls[1].fd = fd;
    polls[1].events = ZMQ_POLLIN;

    int poll_to_stream[2+VISION_STREAM_MAX] = {0};
    int num_polls = 2;
    for (int i=0; i<VISION_STREAM_MAX; i++) {
      if (!streams[i].subscribed) continue;
      polls[num_polls].events = ZMQ_POLLIN;
      if (streams[i].bufs_outstanding >= 2) {
        continue;
      }
      if (streams[i].tb) {
        polls[num_polls].fd = tbuffer_efd(streams[i].tbuffer);
      } else {
        polls[num_polls].fd = poolq_efd(streams[i].queue);
      }
      poll_to_stream[num_polls] = i;
      num_polls++;
    }
    int ret = zmq_poll(polls, num_polls, -1);
    if (ret < 0) {
      if (errno == EINTR || errno == EAGAIN) continue;
      LOGE("poll failed (%d - %d)", ret, errno);
      break;
    }
    if (polls[0].revents) {
      break;
    } else if (polls[1].revents) {
      VisionPacket p;
      err = vipc_recv(fd, &p);
      // printf("recv %d\n", p.type);
      if (err <= 0) {
        break;
      } else if (p.type == VIPC_STREAM_SUBSCRIBE) {
        VisionStreamType stream_type = p.d.stream_sub.type;
        VisionPacket rep = {
          .type = VIPC_STREAM_BUFS,
          .d = { .stream_bufs = { .type = stream_type }, },
        };

        VisionClientStreamState *stream = &streams[stream_type];
        stream->tb = p.d.stream_sub.tbuffer;

        VisionStreamBufs *stream_bufs = &rep.d.stream_bufs;
        if (stream_type == VISION_STREAM_RGB_BACK) {
          stream_bufs->width = s->rgb_width;
          stream_bufs->height = s->rgb_height;
          stream_bufs->stride = s->rgb_stride;
          stream_bufs->buf_len = s->rgb_bufs[0].len;
          rep.num_fds = UI_BUF_COUNT;
          for (int i=0; i<rep.num_fds; i++) {
            rep.fds[i] = s->rgb_bufs[i].fd;
          }
          if (stream->tb) {
            stream->tbuffer = &s->ui_tb;
          } else {
            assert(false);
          }
        } else if (stream_type == VISION_STREAM_RGB_FRONT) {
          stream_bufs->width = s->rgb_front_width;
          stream_bufs->height = s->rgb_front_height;
          stream_bufs->stride = s->rgb_front_stride;
          stream_bufs->buf_len = s->rgb_front_bufs[0].len;
          rep.num_fds = UI_BUF_COUNT;
          for (int i=0; i<rep.num_fds; i++) {
            rep.fds[i] = s->rgb_front_bufs[i].fd;
          }
          if (stream->tb) {
            stream->tbuffer = &s->ui_front_tb;
          } else {
            assert(false);
          }
        } else if (stream_type == VISION_STREAM_YUV) {
          stream_bufs->width = s->yuv_width;
          stream_bufs->height = s->yuv_height;
          stream_bufs->stride = s->yuv_width;
          stream_bufs->buf_len = s->yuv_buf_size;
          rep.num_fds = YUV_COUNT;
          for (int i=0; i<rep.num_fds; i++) {
            rep.fds[i] = s->yuv_ion[i].fd;
          }
          if (stream->tb) {
            stream->tbuffer = s->yuv_tb;
          } else {
            stream->queue = pool_get_queue(&s->yuv_pool);
          }
        } else if (stream_type == VISION_STREAM_YUV_FRONT) {
          stream_bufs->width = s->yuv_front_width;
          stream_bufs->height = s->yuv_front_height;
          stream_bufs->stride = s->yuv_front_width;
          stream_bufs->buf_len = s->yuv_front_buf_size;
          rep.num_fds = YUV_COUNT;
          for (int i=0; i<rep.num_fds; i++) {
            rep.fds[i] = s->yuv_front_ion[i].fd;
          }
          if (stream->tb) {
            stream->tbuffer = s->yuv_front_tb;
          } else {
            stream->queue = pool_get_queue(&s->yuv_front_pool);
          }
        } else {
          assert(false);
        }
        vipc_send(fd, &rep);
        streams[stream_type].subscribed = true;
      } else if (p.type == VIPC_STREAM_RELEASE) {
        // printf("client release f %d  %d\n", p.d.stream_rel.type, p.d.stream_rel.idx);
        int si = p.d.stream_rel.type;
        assert(si < VISION_STREAM_MAX);
        if (streams[si].tb) {
          tbuffer_release(streams[si].tbuffer, p.d.stream_rel.idx);
        } else {
          poolq_release(streams[si].queue, p.d.stream_rel.idx);
        }
        streams[p.d.stream_rel.type].bufs_outstanding--;
      } else {
        assert(false);
      }
    } else {
      int stream_i = VISION_STREAM_MAX;
      for (int i=2; i<num_polls; i++) {
        int si = poll_to_stream[i];
        if (!streams[si].subscribed) continue;
        if (polls[i].revents) {
          stream_i = si;
          break;
        }
      }
      if (stream_i < VISION_STREAM_MAX) {
        streams[stream_i].bufs_outstanding++;
        int idx;
        if (streams[stream_i].tb) {
          idx = tbuffer_acquire(streams[stream_i].tbuffer);
        } else {
          idx = poolq_pop(streams[stream_i].queue);
        }
        if (idx < 0) {
          break;
        }
        VisionPacket rep = {
          .type = VIPC_STREAM_ACQUIRE,
          .d = {.stream_acq = {
            .type = (VisionStreamType)stream_i,
            .idx = idx,
          }},
        };
        if (stream_i == VISION_STREAM_YUV) {
          rep.d.stream_acq.extra.frame_id = s->yuv_metas[idx].frame_id;
          rep.d.stream_acq.extra.timestamp_eof = s->yuv_metas[idx].timestamp_eof;
        } else if (stream_i == VISION_STREAM_YUV_FRONT) {
          rep.d.stream_acq.extra.frame_id = s->yuv_front_metas[idx].frame_id;
          rep.d.stream_acq.extra.timestamp_eof = s->yuv_front_metas[idx].timestamp_eof;
        }
        vipc_send(fd, &rep);
      }
    }
  }

  LOGW("client end fd %d", fd);

  for (int i=0; i<VISION_STREAM_MAX; i++) {
    if (!streams[i].subscribed) continue;
    if (streams[i].tb) {
      t