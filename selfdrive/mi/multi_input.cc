#include "multi_input.h"
using namespace std;

std::unique_ptr<zdl::SNPE::SNPE> snpe;

float *output;

zdl::DlSystem::Runtime_t checkRuntime()
{
    static zdl::DlSystem::Version_t Version = zdl::SNPE::SNPEFactory::getLibraryVersion();
    static zdl::DlSystem::Runtime_t Runtime;
    std::cout << "SNPE Version: " << Version.asString().c_str() << std::endl; //Print Version number
    std::cout << "\ntest";
    if (zdl::SNPE::SNPEFactory::isRuntimeAvailable(zdl::DlSystem::Runtime_t::GPU)) {
        Runtime = zdl::DlSystem::Runtime_t::GPU;
    } else {
        Runtime = zdl::DlSystem::Runtime_t::CPU;
    }

    return Runtime;
}

void initializeSNPE(zdl::DlSystem::Runtime_t runtime) {
  std::unique_ptr<zdl::DlContainer::IDlContainer> container;
  container = zdl::DlContainer::IDlContainer::open("/data/openpilot/selfdrive/mi/multi_input.dlc");
  //printf("loaded model\n");
  int counter = 0;
  zdl::SNPE::SNPEBuilder snpeBuilder(container.get());
  snpe = snpeBuilder.setOutputLayers({})
                      .setRuntimeProcessor(runtime)
                      .setUseUserSuppliedBuffers(false)
                      .setPerformanceProfile(zdl::DlSystem::PerformanceProfile_t::HIGH_PERFORMANCE)
                      .build();
}



void loadInputTensor(std::unique_ptr<zdl::SNPE::SNPE> &snpe, std::vector<float> inputVec) {
  std::unique_ptr<zdl::DlSystem::ITensor> input;
  const auto &strList_opt = snpe->getInputTensorNames();
  if (!strList_opt) throw std::runtime_error("Error obtaining Input tensor names");
  const auto &strList = *strList_opt;

  const auto &inputDims_opt = snpe->getInputDimensions(strList.at(0));
  //const auto &inputShape = *inputDims_opt;
  //std::cout << "input shape: " << inputShape << "\n";

  //input = zdl::SNPE::SNPEFactory::getTensorFactory().createTensor(inputShape);
  //std::copy(inputVec.begin(), inputVec.end(), input->begin());

  //return input;
}

float returnOutput(const zdl::DlSystem::ITensor* tensor) {
  float op = *tensor->cbegin();
  return op;
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

extern "C" {

  void init_model(){
    zdl::DlSystem::Runtime_t runt=checkRuntime();
    initializeSNPE(runt);
  }

  float run_model(float a, float b){
    std::vector<float> inputVec;
    std::vector<float> inputVec2;
    inputVec.push_back(a);
    inputVec2.push_back(b);
    printf("about to get input tensor");
    std::unique_ptr<zdl::DlSystem::ITensor> inputTensor = loadInputTensor(snpe, inputVec);
    //std::unique_ptr<zdl::DlSystem::ITensor> inputTensor2 = loadInputTensor(snpe, inputVec2);
    printf("about to execute model");
    //zdl::DlSystem::ITensor* oTensor = executeNetwork(snpe, inputTensor);
    //printf("about to get output");
    //return returnOutput(oTensor);
    return 1.5;
  }

  float run_model_live_tracks(float inputData[54]){
    int size = 54;
    std::vector<float> inputVec;
    for (int i = 0; i < size; i++ ) {
      inputVec.push_back(inputData[i]);
    }

    std::unique_ptr<zdl::DlSystem::ITensor> inputTensor = loadInputTensor(snpe, inputVec);
    zdl::DlSystem::ITensor* oTensor = executeNetwork(snpe, inputTensor);
    return returnOutput(oTensor);
    }

  float run_model_lstm(float inputData[60]){
    int size = 60;
    std::vector<float> inputVec;
    for (int i = 0; i < size; i++ ) {
      inputVec.push_back(inputData[i]);
    }

    std::unique_ptr<zdl::DlSystem::ITensor> inputTensor = loadInputTensor(snpe, inputVec);
    zdl::DlSystem::ITensor* oTensor = executeNetwork(snpe, inputTensor);
    return returnOutput(oTensor);
  }


int main(){
  std::cout << "hello";
  return 0;
}

}
