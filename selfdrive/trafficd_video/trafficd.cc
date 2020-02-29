#include "traffic.h"

using namespace std;

std::unique_ptr<zdl::SNPE::SNPE> snpe;
std::unique_ptr<zdl::DlSystem::ITensor> input;



volatile sig_atomic_t do_exit = 0;

const std::vector<std::string> modelLabels = {"RED", "GREEN", "YELLOW", "NONE"};
const double modelRate = 1 / 5.;  // 5 Hz

const int image_stride = 3840;  // global constants
const int original_shape[3] = {874, 1164, 3};
const int original_size = 874 * 1164 * 3;
const int cropped_shape[3] = {515, 814, 3};
const int cropped_size = 515 * 814 * 3;

const float pixel_norm = 255.0;
const int horizontal_crop = 175;
const int top_crop = 0;
const int hood_crop = 209;
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
    container = zdl::DlContainer::IDlContainer::open("../../models/video_test.dlc");
    zdl::SNPE::SNPEBuilder snpeBuilder(container.get());
    snpe = snpeBuilder.setOutputLayers({})
                      .setRuntimeProcessor(runtime)
                      .setUseUserSuppliedBuffers(false)
                      .setPerformanceProfile(zdl::DlSystem::PerformanceProfile_t::HIGH_PERFORMANCE)
                      .setCPUFallbackMode(true)
                      .build();
    const auto &strList_opt = snpe->getInputTensorNames();

    if (!strList_opt) throw std::runtime_error("Error obtaining Input tensor names");
    const auto &strList = *strList_opt;
    assert (strList.size() == 1);
    std::cout << "time: " << millis_since_boot() - startTime << " ms\n";

    const auto &inputDims_opt = snpe->getInputDimensions(strList.at(0));
    const auto &inputShape = *inputDims_opt;

    input = zdl::SNPE::SNPEFactory::getTensorFactory().createTensor(inputShape);
}

std::unique_ptr<zdl::DlSystem::ITensor> loadInputTensor(std::unique_ptr<zdl::SNPE::SNPE> &snpe, std::vector<float> inputVec) {
    double startTime = millis_since_boot();


    /* Copy the loaded input file contents into the networks input tensor. SNPE's ITensor supports C++ STL functions like std::copy() */

    std::cout << "time: " << millis_since_boot() - startTime << " ms\n";
    std::copy(inputVec.begin(), inputVec.end(), input->begin());
    std::cout << "time: " << millis_since_boot() - startTime << " ms\n";
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

std::vector<float> runModel(std::vector<float> inputVector) {
    std::unique_ptr<zdl::DlSystem::ITensor> inputTensor = loadInputTensor(snpe, inputVector);  // inputVec)

    zdl::DlSystem::ITensor* tensor = executeNetwork(snpe, inputTensor);

    std::vector<float> outputVector;
    for (auto it = tensor->cbegin(); it != tensor->cend(); ++it ){
        float op = *it;
        outputVector.push_back(op);
        std::cout << op << std::endl;
    }
    std::cout << "---\n";
    return outputVector;
}

void sleepFor(double sec) {
    usleep(sec * secToUs);
}

void set_do_exit(int sig) {
    std::cout << "received signal: " << sig << std::endl;
    do_exit = 1;
}


int main(){
    signal(SIGINT, (sighandler_t)set_do_exit);
    signal(SIGTERM, (sighandler_t)set_do_exit);

    initModel(); // init stuff

    VisionStream stream;

    Context* c = Context::create();

    while (!do_exit){  // keep traffic running in case we can't get a frame (mimicking modeld)
        double loopStart;
        double loopEnd;
        double lastLoop = 0;

        while (!do_exit){
            loopStart = millis_since_boot();
            std::vector<float> images;
            ifstream infile("/data/openpilot/selfdrive/trafficd_video/images/video");
            string line;
            if (infile.is_open()){
                while(infile.good()){
                    getline(infile, line);
                    images.push_back(stoi(line) / 255.0);
                }
            }
            infile.close();
            std::cout << "Vector size: " << images.size() << std::endl;
            double startTime = millis_since_boot();
            std::vector<float> modelOutputVec = runModel(images);
            double endTime = millis_since_boot();
            std::cout << "time to predict: " << endTime - startTime << " ms\n";
            return 0;
        }
    }
    std::cout << "trafficd is dead" << std::endl;
    visionstream_destroy(&stream);
    return 0;
}
