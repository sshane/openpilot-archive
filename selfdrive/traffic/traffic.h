#include <SNPE/SNPE.hpp>
#include <SNPE/SNPEBuilder.hpp>
#include <SNPE/SNPEFactory.hpp>
#include <DlContainer/IDlContainer.hpp>
#include <DlSystem/DlError.hpp>
#include <DlSystem/ITensor.hpp>
#include <DlSystem/ITensorFactory.hpp>
#include <DlSystem/IUserBuffer.hpp>
#include <DlSystem/IUserBufferFactory.hpp>
#include <Util/Util.cpp>
#include <string>
#include <sstream>
#include <iostream>
#include <fstream>
#include <array>

extern "C"{
  void init_model();
  float run_model();
  void multi_test(double inputArray[582][437][3], int x, int y, int z);
  void predict_traffic(int inputArray[1257630], float* outputArray);
}