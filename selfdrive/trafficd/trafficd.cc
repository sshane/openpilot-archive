#include "traffic.h"

using namespace std;

std::unique_ptr<zdl::SNPE::SNPE> snpe;
volatile sig_atomic_t do_exit = 0;

// const std::vector<std::string> modelLabels = {"RED", "GREEN", "YELLOW", "NONE"};
const double modelRate = 1 / 5.;  // 5 Hz

const int image_stride = 3840;  // global constants
const int cropped_size = 515 * 814 * 3;
const int cropped_shape[3] = {515, 814, 3};

const float pixel_norm = 255.0;
const int horizontal_crop = 175;
const int top_crop = 150;
const int offset = horizontal_crop * cropped_shape[2];
const double msToSec = 1 / 1000.;  // multiply
const double secToUs = 1e+6;

zdl::DlSystem::Runtime_t checkRuntime() {
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
    container = zdl::DlContainer::IDlContainer::open("../../models/traffic_model.dlc");
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

    /* Copy the loaded input file contents into the networks input tensor. SNPE's ITensor supports C++ STL functions like std::copy() */
    std::copy(inputVec.begin(), inputVec.end(), input->begin());
    return input;
}

zdl::DlSystem::ITensor* executeNetwork(std::unique_ptr<zdl::SNPE::SNPE>& snpe, std::unique_ptr<zdl::DlSystem::ITensor>& input) {
    static zdl::DlSystem::TensorMap outputTensorMap;
    snpe->execute(input.get(), outputTensorMap);
    zdl::DlSystem::StringList tensorNames = outputTensorMap.getTensorNames();

    const char* name = tensorNames.at(0);  // only should the first
    auto tensorPtr = outputTensorMap.getTensor(name);
    return tensorPtr;
}

void setModelOutput(const zdl::DlSystem::ITensor* tensor, float* outputArray) {
    int counter = 0;
    for (auto it = tensor->cbegin(); it != tensor->cend(); ++it ){
        float op = *it;
        outputArray[counter] = op;
        counter += 1;
    }
}

void initModel() {
    zdl::DlSystem::Runtime_t runt=checkRuntime();
    initializeSNPE(runt);
}

//void initVisionStream(){
//    int err;
//    while (true) {
//        err = visionstream_init(&stream, VISION_STREAM_RGB_BACK, true, &buf_info);
//        if (err != 0) {
//            printf("visionstream fail\n");
//            usleep(100000);
//        }
//        break;
//    }
//}

//int getStreamBuffer(){
//    buf = visionstream_get(&stream, &extra);
//    if (buf == NULL) {
//        printf("visionstream get failed\n");
//        return 1;
//    }
//    return 0;
//}

std::vector<float> processStreamBuffer(VIPCBuf* buf) {
    uint8_t *src_ptr = (uint8_t *)buf->addr;
    src_ptr += (top_crop * image_stride); // starting offset of 150 lines of stride in

    std::vector<float> outputVector;
    for (int line = 0; line < cropped_shape[0]; line++) {
        for(int line_pos = 0; line_pos < (cropped_shape[1] * cropped_shape[2]); line_pos += cropped_shape[2]) {
            outputVector.push_back(src_ptr[line_pos + offset + 0] / pixel_norm);
            outputVector.push_back(src_ptr[line_pos + offset + 1] / pixel_norm);
            outputVector.push_back(src_ptr[line_pos + offset + 2] / pixel_norm);
        }
        src_ptr += image_stride;
    }
    return outputVector;
}

void sendPrediction(float modelOutput[], PubSocket* traffic_lights_sock) {
    kj::ArrayPtr<const float> modelOutput_vs(&modelOutput[0], 4);

    capnp::MallocMessageBuilder msg;
    cereal::Event::Builder event = msg.initRoot<cereal::Event>();
    event.setLogMonoTime(nanos_since_boot());
    auto traffic_lights = event.initTrafficModelRaw();
    traffic_lights.setPrediction(modelOutput_vs);

    auto words = capnp::messageToFlatArray(msg);
    auto bytes = words.asBytes();
    traffic_lights_sock->send((char*)bytes.begin(), bytes.size());
}

std::vector<float> runModel(std::vector<float> inputVector) {
    std::unique_ptr<zdl::DlSystem::ITensor> inputTensor = loadInputTensor(snpe, inputVector);  // inputVec)
    zdl::DlSystem::ITensor* tensor = executeNetwork(snpe, inputTensor);

    std::vector<float> outputVector;
    for (auto it = tensor->cbegin(); it != tensor->cend(); ++it ){
        float op = *it;
        outputVector.push_back(op);
    }
    return outputVector;
}

bool shouldStop() {
    std::ifstream infile("/data/openpilot/selfdrive/trafficd/stop");
    return infile.good();
}

void sleepFor(double sec) {
    usleep(sec * secToUs);
}

double rateKeeper(double loopTime, double lastLoop) {
    double toSleep;
    if (lastLoop < 0){  // don't sleep if last loop lagged
        lastLoop = std::max(lastLoop, -modelRate);  // this should ensure we don't keep adding negative time to lastLoop if a frame lags pretty badly
                                                    // negative time being time to subtract from sleep time
        // std::cout << "Last frame lagged by " << -lastLoop << " seconds. Sleeping for " << modelRate - (loopTime * msToSec) + lastLoop << " seconds" << std::endl;
        toSleep = modelRate - (loopTime * msToSec) + lastLoop;  // keep time as close as possible to our rate, this reduces the time slept this iter
    } else {
        toSleep = modelRate - (loopTime * msToSec);
    }
    if (toSleep > 0){  // don't sleep for negative time, in case loop takes too long one iteration
        sleepFor(toSleep);
    } else {
        std::cout << "trafficd lagging by " << -(toSleep / msToSec) << " ms." << std::endl;
    }
    return toSleep;
}

void set_do_exit(int sig) {
    std::cout << "received signal: " << sig << std::endl;
    do_exit = 1;
}

uint8_t clamp(int16_t value) {
    return value<0 ? 0 : (value>255 ? 255 : value);
}

static uint8_t* yuv420p_to_rgb2(const uint8_t* y, const uint8_t* u, const uint8_t* v, const size_t width, const size_t height, const bool returnBGR) {
    // returns RGB if returnBGR is false
    const size_t size = width * height;
    uint8_t* rgb = (uint8_t*)calloc((989*874*3), sizeof(uint8_t));

    int b ,g, r;
    uint8_t* src_ptr = rgb;
    for (int j = 0; j < height; j++) {
        for (int i = 0; i < width; i++) {
            if (width < 175 | width > (1164-175)){
                continue;
            }
            int yy = y[(j * width) + i];
            int uu = u[((j / 2) * (width / 2)) + (i / 2)];
            int vv = v[((j / 2) * (width / 2)) + (i / 2)];

            if (returnBGR){
                b = 1.164 * (yy - 16) + 1.596 * (vv - 128);
                g = 1.164 * (yy - 16) - 0.813 * (vv - 128) - 0.391 * (uu - 128);
                r = 1.164 * (yy - 16) + 2.018 * (uu - 128);
            } else {
                r = 1.164 * (yy - 16) + 1.596 * (vv - 128);
                g = 1.164 * (yy - 16) - 0.813 * (vv - 128) - 0.391 * (uu - 128);
                b = 1.164 * (yy - 16) + 2.018 * (uu - 128);
            }
            *src_ptr++ = clamp(r);
            *src_ptr++ = clamp(g);
            *src_ptr++ = clamp(b);
        }
    }
    return rgb;
}

int main(){
    signal(SIGINT, (sighandler_t)set_do_exit);
    signal(SIGTERM, (sighandler_t)set_do_exit);

    //initModel(); // init stuff

    VisionStream stream;

    Context* c = Context::create();
    PubSocket* traffic_lights_sock = PubSocket::create(c, "trafficModelRaw");
    assert(traffic_lights_sock != NULL);

    while (!do_exit){  // keep traffic running in case we can't get a frame (mimicking modeld)
        VisionStreamBufs buf_info;
        int err = visionstream_init(&stream, VISION_STREAM_YUV, true, &buf_info);
        if (err != 0) {
            printf("trafficd: visionstream fail\n");
            usleep(100000);
        }

        double loopStart;
        double loopEnd;
        double lastLoop = 0;
        while (!do_exit){
            loopStart = millis_since_boot();

            VIPCBuf* buf;
            VIPCBufExtra extra;

            buf = visionstream_get(&stream, &extra);
            if (buf == NULL) {
                printf("trafficd: visionstream get failed\n");
                break;
            }
            uint8_t* img;

            uint8_t *y = (uint8_t*)buf->addr;
            uint8_t *u = y + (buf_info.width*buf_info.height);
            uint8_t *v = u + (buf_info.width/2)*(buf_info.height/2);

            // img = malloc(3052008);

            img = yuv420p_to_rgb2(y, u, v, buf_info.width, buf_info.height, false);

//            void* temp = malloc(img.size());
//            uint8_t *dst_ptr = (uint8_t *)temp;
//
//            for (int i = 0; i < img.size(); i++){
//                dst_ptr[i] = img[i];
//            }
            FILE *f;
            f = fopen("/data/buffer1", "wb");
            fwrite((uint8_t *)img, 1, 989*874*3, f);


            uint8_t *src_ptr = (uint8_t *)img;
//            src_ptr += (top_crop * image_stride); // starting offset of 150 lines of stride in

            std::vector<int> outputVector;
            int idx = 0;
            for (int x = 0; x < 1164; x++) {
                for (int y = 0; y < 874; y++) {
                    outputVector.push_back(src_ptr[idx]);
                    outputVector.push_back(src_ptr[idx + 1]);
                    outputVector.push_back(src_ptr[idx + 2]);
                    idx += 3;
                }
            }

//            for (int line = 0; line < cropped_shape[0]; line++) {
//                for(int line_pos = 0; line_pos < (cropped_shape[1] * cropped_shape[2]); line_pos += cropped_shape[2]) {
//                    outputVector.push_back(src_ptr[line_pos + offset + 0]);
//                    outputVector.push_back(src_ptr[line_pos + offset + 1]);
//                    outputVector.push_back(src_ptr[line_pos + offset + 2]);
//                }
//                src_ptr += image_stride;
//            }
            std::cout << "Size of vector: " << outputVector.size() << std::endl;
            ofstream outputfile("/data/cropped");
            std::copy(outputVector.rbegin(), outputVector.rend(), std::ostream_iterator<int>(outputfile, "\n"));

//            YUV2RGB(buf->addr, img, buf_info.width, buf_info.height, 1);

//            Mat mYUV(buf_info.height + buf_info.height/2, buf_info.width, CV_8UC1, (void*) buf->addr);
//            Mat mRGB(buf_info.height, buf_info.width, CV_8UC3);
//            cvtColor(mYUV, mRGB, CV_YUV2RGB_YV12, 3);



//            for (int i = 0; i < 10; i++) {
//                std::cout << "Y: " << y[i] << " U: " << u[i] << " V: " << v[i] << std::endl;
//            }


//            std::cout << "buf size: " << buf_info.buf_len << std::endl;

            return 1;

            /*

            std::vector<float> inputVector = processStreamBuffer(buf);  // writes float vector to inputVector
            // std::cout << "Vector elements: " << inputVector.size() << std::endl;

            // std::vector<float> outputVector = runModel(processStreamBuffer(buf)); todo: <- test
            std::vector<float> outputVector = runModel(inputVector);

            float modelOutput[4];
            for (int i = 0; i < 4; i++){  // convert vector to array
                modelOutput[i] = outputVector[i];
                // std::cout << modelOutput[i] << std::endl;
            }
            // std::cout << std::endl;

            // std::cout << "Prediction: " << modelLabels[pred_idx] << " (" << modelOutput[pred_idx] * 100 << "%)" << std::endl;

            sendPrediction(modelOutput, traffic_lights_sock);*/

            loopEnd = millis_since_boot();
            // std::cout << "Loop time: " << loopEnd - loopStart << " ms\n";

            lastLoop = rateKeeper(loopEnd - loopStart, lastLoop);
            // std::cout << "Current frequency: " << 1 / ((millis_since_boot() - loopStart) * msToSec) << " Hz" << std::endl;

            // if (shouldStop()){
            //     break;
            // }
        }
    }
    visionstream_destroy(&stream);
    return 0;
}
