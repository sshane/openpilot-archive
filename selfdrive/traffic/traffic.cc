#include "traffic.h"
using namespace std;

std::unique_ptr<zdl::SNPE::SNPE> snpe;

float *output;

zdl::DlSystem::Runtime_t checkRuntime()
{
    static zdl::DlSystem::Version_t Version = zdl::SNPE::SNPEFactory::getLibraryVersion();
    static zdl::DlSystem::Runtime_t Runtime;
    std::cout << "SNPE Version: " << Version.asString().c_str() << std::endl; //Print Version number
    if (zdl::SNPE::SNPEFactory::isRuntimeAvailable(zdl::DlSystem::Runtime_t::GPU)) {
        Runtime = zdl::DlSystem::Runtime_t::GPU;
    } else {
        Runtime = zdl::DlSystem::Runtime_t::CPU;
    }
    return Runtime;
}

void initializeSNPE(zdl::DlSystem::Runtime_t runtime) {
  std::unique_ptr<zdl::DlContainer::IDlContainer> container;
  container = zdl::DlContainer::IDlContainer::open("/data/openpilot/selfdrive/traffic/models/trafficv5moredata.dlc");
  //printf("loaded model\n");
  int counter = 0;
  zdl::SNPE::SNPEBuilder snpeBuilder(container.get());
  snpe = snpeBuilder.setOutputLayers({})
                      .setRuntimeProcessor(runtime)
                      .setUseUserSuppliedBuffers(false)
                      .setPerformanceProfile(zdl::DlSystem::PerformanceProfile_t::HIGH_PERFORMANCE)
                      .build();
}


std::unique_ptr<zdl::DlSystem::ITensor> loadInputTensor(std::unique_ptr<zdl::SNPE::SNPE> &snpe, std::vector<float> inputVec) {
  std::unique_ptr<zdl::DlSystem::ITensor> input;
  const auto &strList_opt = snpe->getInputTensorNames();
  if (!strList_opt) throw std::runtime_error("Error obtaining Input tensor names");
  const auto &strList = *strList_opt;
  std::cout << strList_opt;

  const auto &inputDims_opt = snpe->getInputDimensions(strList.at(0));
  const auto &inputShape = *inputDims_opt;

  input = zdl::SNPE::SNPEFactory::getTensorFactory().createTensor(inputShape);
  std::copy(inputVec.begin(), inputVec.end(), input->begin());

  return input;
}

std::unique_ptr<zdl::DlSystem::ITensor> loadInputTensorNew(std::unique_ptr<zdl::SNPE::SNPE> &snpe, std::vector<float> inputVec) {
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

int returnOutputMulti(const zdl::DlSystem::ITensor* tensor) {
    vector<float> outputs;
    for (auto it = tensor->cbegin(); it != tensor->cend(); ++it ){
        float op = *it;
        std::cout << op << "\n";
        outputs.push_back(op);
    }
    int maxElementIndex = std::max_element(outputs.begin(), outputs.end()) - outputs.begin();
    return maxElementIndex;
//  float gas = outputs.at(0);
//  float brake = outputs.at(1);
//  if (gas > brake) {
//    return gas;
//  } else if (brake > gas){
//    return -brake;
//  } else {
//    return 0.0;
//  }
}

extern "C" {
    void init_model(){
        zdl::DlSystem::Runtime_t runt=checkRuntime();
        initializeSNPE(runt);
    }

    void multi_test(double inputArray[582][437][3], int x, int y, int z){
//        std::cout << x;
//        std::cout << "\n";
//        std::cout << y;
//        std::cout << "\n";
//        std::cout << z;
//        std::cout << "\n";

        std::vector < std::vector < std::vector<float> > > inputVec;
        std::vector<float> newInputVec;

        for (int i = 0; i < x; ++i) {
            inputVec.push_back(std::vector<std::vector<float> >());
            for (int j = 0; j < y; ++j) {
                inputVec[i].push_back(std::vector<float>());
                for (int k = 0; k < z; ++k){
                    inputVec[i][j].push_back(inputArray[i][j][k]);
                    newInputVec.push_back(inputArray[i][j][k]);
                    // std::cout << inputArray[i][j][k] << "\n";
                    // std::cout << inputArray[i][j][k] << "\n";
                    // std::cout << inputVec[i][j][k] << '\n';
                }
            }
        }

        std::unique_ptr<zdl::DlSystem::ITensor> inputTensor = loadInputTensorNew(snpe, newInputVec);  // inputVec)
        zdl::DlSystem::ITensor* oTensor = executeNetwork(snpe, inputTensor);
        returnOutputMulti(oTensor);
    }

    int predict_traffic(float inputArray[3]){
        return 0;
//        int size = 2322180;
//        std::vector<float> inputVec;
//        for (int i = 0; i < size; i++ ) {
//            inputVec.push_back(inputArray[i]);
//        }
//
//        std::unique_ptr<zdl::DlSystem::ITensor> inputTensor = loadInputTensorNew(snpe, inputVec);  // inputVec)
//        zdl::DlSystem::ITensor* oTensor = executeNetwork(snpe, inputTensor);
//        return returnOutputMulti(oTensor);
    }

    float run_model(){
      int size = 49;
    //      std::unique_ptr<zdl::DlSystem::ITensor> inputTensor = loadInputTensorNew(snpe, inputVec);
    //      executeNetwork (snpe , inputTensor); // ITensor

    //      std::vector<float> inputVec;
    //      for (int i = 0; i < size; i++ ) {
    //        inputVec.push_back(inputData[i]);
    //      }
    //
    //      std::unique_ptr<zdl::DlSystem::ITensor> inputTensor = loadInputTensor(snpe, inputVec);
    //      zdl::DlSystem::ITensor* oTensor = executeNetwork(snpe, inputTensor);
      return 1.0;
    //      return returnOutput(oTensor);
    }

    int main(){
      std::cout << "hello";
      return 0;
    }

}