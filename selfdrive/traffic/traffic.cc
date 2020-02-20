#include "traffic.h"

#include <stdio.h>
#include <stdlib.h>

#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <unistd.h>
#include <zmq.h>

#include "common/visionbuf.h"
#include "common/visionipc.h"
#include "common/swaglog.h"
#include "common/timing.h"

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

int visionTest(){
    int err;
    double t1 = millis_since_boot();
    VisionStream stream;

    VisionStreamBufs buf_info;
    while (true) {
        err = visionstream_init(&stream, VISION_STREAM_RGB_BACK, true, &buf_info);
        if (err != 0) {
            printf("visionstream fail\n");
            usleep(100000);
        }
        break;
    }

    VIPCBufExtra extra;
    VIPCBuf* buf = visionstream_get(&stream, &extra);
    if (buf == NULL) {
        printf("visionstream get failed\n");
        return 1;
    }

    double t2 = millis_since_boot();

    printf("fetch time:   %.2f\n", (t2-t1));

    int image_width = 1164;
    int image_height = 874;
    //int image_stride = 3840;
    //int padding = 348;


    std::vector<float> modelInput;

    int y_hood_crop = 665;
    int horizontal_crop = 175;

    void* img = malloc(1257630);
    uint8_t *dst_ptr = (uint8_t *)img;
    uint8_t *src_ptr = (uint8_t *)buf->addr;

    src_ptr += (150 * 3840); // starting offset of 150 lines of stride in

    int idx = 0;
    for(int line=0;line<=515;line++) {
        for(int line_pos = 0; line_pos <= (814 * 3); line_pos += 3) {
            int offset = 175 * 3;
            if (idx < 1000){
                //std::cout << src_ptr[line_pos + offset + 0] << " " << src_ptr[line_pos + offset + 1] << " " << src_ptr[line_pos + offset + 2] << std::endl;
//                printf("%i\n", src_ptr[line_pos + offset + 0]);
            }
//            idx++;
            modelInput.push_back(src_ptr[line_pos + offset + 0] / 255.);
            modelInput.push_back(src_ptr[line_pos + offset + 1] / 255.);
            modelInput.push_back(src_ptr[line_pos + offset + 2] / 255.);

            dst_ptr[line_pos + 0] = src_ptr[line_pos + offset + 2];
            dst_ptr[line_pos + 1] = src_ptr[line_pos + offset + 1];
            dst_ptr[line_pos + 2] = src_ptr[line_pos + offset + 0];
        }
        dst_ptr += 2442; // x = 814 * 3 pixels = 2442 bytes per horizontal line
        src_ptr += 3840; // stride
    }

    std::cout << "Vector elements: " << modelInput.size() << std::endl;

    double t3 = millis_since_boot();

    printf("process time: %.2f\n", (t3-t2));

    std::ofstream ofile;
    ofile.open("/data/openpilot/selfdrive/traffic/img_flat", std::ios::app);
    int counter123=0;
    for(int i=0; i<modelInput.size(); i++) {
        if (counter123 < 50){
            std::cout << modelInput[i] << std::endl;
        }
        ofile << modelInput[i] << std::endl;
        counter123++;
    }
    ofile.close();


    FILE *f = fopen("/data/openpilot/selfdrive/traffic/img_buffer", "wb");
    fwrite((uint8_t *)img, 1, 1257630, f);
    free(img);
    fclose(f);

    double t4 = millis_since_boot();

    printf("write time:   %.2f\n", (t4-t3));

    visionstream_destroy(&stream);

    double t5 = millis_since_boot();

    printf("total time:   %.2f\n", (t5-t1));

    return 0;
}

    int main(){
      return 0;
    }
}