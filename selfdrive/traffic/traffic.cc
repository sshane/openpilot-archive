#include "traffic.h"

#include <stdio.h>
#include <stdlib.h>

#include "common/visionbuf.h"
#include "common/visionipc.h"
#include "common/swaglog.h"

using namespace std;

std::unique_ptr<zdl::SNPE::SNPE> snpe;

zdl::DlSystem::Runtime_t checkRuntime()
{
    static zdl::DlSystem::Version_t Version = zdl::SNPE::SNPEFactory::getLibraryVersion();
    static zdl::DlSystem::Runtime_t Runtime;
    std::cout << "SNPE Version: " << Version.asString().c_str() << std::endl; //Print Version number
    if (zdl::SNPE::SNPEFactory::isRuntimeAvailable(zdl::DlSystem::Runtime_t::GPU)) {
        Runtime = zdl::DlSystem::Runtime_t::GPU;  // todo: using CPU
    } else {
        Runtime = zdl::DlSystem::Runtime_t::CPU;
    }
    return Runtime;
}

void initializeSNPE(zdl::DlSystem::Runtime_t runtime) {
  std::unique_ptr<zdl::DlContainer::IDlContainer> container;
  container = zdl::DlContainer::IDlContainer::open("/data/openpilot/selfdrive/traffic/models/trafficv6.dlc");
  zdl::SNPE::SNPEBuilder snpeBuilder(container.get());
  snpe = snpeBuilder.setOutputLayers({})
                      .setRuntimeProcessor(runtime)
                      .setUseUserSuppliedBuffers(false)
                      .setPerformanceProfile(zdl::DlSystem::PerformanceProfile_t::HIGH_PERFORMANCE)
                      .setCPUFallbackMode(true)
                      .build();
}

std::unique_ptr<zdl::DlSystem::ITensor> loadInputTensor(std::unique_ptr<zdl::SNPE::SNPE> &snpe, std::vector<float> inputVec) {
    std::unique_ptr<zdl::DlSystem::ITensor> input;
    const auto &strList_opt = snpe->getInputTensorNames();

    if (!strList_opt) throw std::runtime_error("Error obtaining Input tensor names");
    const auto &strList = *strList_opt;
    assert (strList.size() == 1);

    const auto &inputDims_opt = snpe->getInputDimensions(strList.at(0));
    const auto &inputShape = *inputDims_opt;

    input = zdl::SNPE::SNPEFactory::getTensorFactory().createTensor(inputShape);
    /* Copy the loaded input file contents into the networks input tensor.SNPE's ITensor supports C++ STL functions like std::copy() */

    std::copy(inputVec.begin(), inputVec.end(), input->begin());
    return input;

}

zdl::DlSystem::ITensor* executeNetwork(std::unique_ptr<zdl::SNPE::SNPE>& snpe,
                    std::unique_ptr<zdl::DlSystem::ITensor>& input) {
  static zdl::DlSystem::TensorMap outputTensorMap;
  snpe->execute(input.get(), outputTensorMap);
  zdl::DlSystem::StringList tensorNames = outputTensorMap.getTensorNames();

  const char* name = tensorNames.at(0);  // only should the first
  auto tensorPtr = outputTensorMap.getTensor(name);
  return tensorPtr;
}

void setModelOutput(const zdl::DlSystem::ITensor* tensor, float* outputArray) {
    // vector<float> outputs;
    int counter = 0;
    for (auto it = tensor->cbegin(); it != tensor->cend(); ++it ){
        float op = *it;
        // outputs.push_back(op);
        outputArray[counter] = op;
        counter += 1;
    }
}

extern "C" {
    void initModel(){
        zdl::DlSystem::Runtime_t runt=checkRuntime();
        initializeSNPE(runt);
    }

    void predictTraffic(int inputArray[1257630], float* outputArray){
        int size = 1257630;
        std::vector<float> inputVec;
        for (int i = 0; i < size; i++ ) {
            inputVec.push_back(inputArray[i] / 255.0);
        }
        //delete[] inputArray;

        std::unique_ptr<zdl::DlSystem::ITensor> inputTensor = loadInputTensor(snpe, inputVec);  // inputVec)
        zdl::DlSystem::ITensor* oTensor = executeNetwork(snpe, inputTensor);

        setModelOutput(oTensor, outputArray);
    }

    void visionTest(){
        std::cout << "here" << std::endl;
        VisionStreamBufs buf_info;
        VisionStream stream;
        int err = visionstream_init(&stream, VISION_STREAM_YUV, true, &buf_info);
        if (err) {
            printf("visionstream connect fail\n");
        } else {
            printf("Success!\n");
        }
        std::cout << "connected with buffer size: " << buf_info.buf_len << std::endl;

        cl_device_id device_id;
        cl_context context;

        cl_mem yuv_cl;
        VisionBuf yuv_ion = visionbuf_allocate_cl(buf_info.buf_len, device_id, context, &yuv_cl);

        VIPCBuf *buf;
        VIPCBufExtra extra;
        buf = visionstream_get(&stream, &extra);

        if (buf == NULL) {
            printf("visionstream get failed\n");
        }
        uint8_t *y = (uint8_t*)buf->addr;
        uint8_t *u = y + (buf_info.width*buf_info.height);
        uint8_t *v = u + (buf_info.width/2)*(buf_info.height/2);

        FILE *f = fopen("/data/openpilot/selfdrive/traffic/testy", "wb");
        uint8_t *buf_ptr = (uint8_t*)buf->addr;

        fwrite(y, 1, y.buf_len, f);
        fclose(f);

//        std::cout << yuv_ion.addr << std::endl;
//        std::cout << buf->addr << std::endl;
//        memcpy(yuv_ion.addr, buf->addr, buf_info.buf_len);

        //float *new_frame_buf = frame_prepare(&s->frame, q, yuv_cl, width, height, transform);  // need to use this function, but don't have a modelstate to input. probably need to rewrite this function and what is uses
    }

    int main(){
      return 0;
    }
}