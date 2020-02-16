#include "traffic.h"
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
//    std::vector<float> inputVec = loadFloatDataFile("/data/openpilot/selfdrive/traffic/GREEN.png");

//    for (std::vector<int>::size_type i = 0; i < 500; i++) {
//	    std::cout << inputVec.at(i) << '\n';
//    }

//    double max = *max_element(inputVec.begin(), inputVec.end());
//    cout<<"Max value: "<<max<<endl;
//    double min = *min_element(inputVec.begin(), inputVec.end());
//    cout<<"Min value: "<<min<<endl;

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
        std::cout << op << "\n";
        // outputs.push_back(op);
        outputArray[counter] = op;
        std::cout << outputArray[counter] << "-test\n";
        counter += 1;
    }
}

extern "C" {
    void init_model(){
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

    int main(){
      return 0;
    }
}