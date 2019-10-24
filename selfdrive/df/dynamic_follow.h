#include <SNPE/SNPE.hpp>
#include <SNPE/SNPEBuilder.hpp>
#include <SNPE/SNPEFactory.hpp>
#include <DlContainer/IDlContainer.hpp>
#include <DlSystem/DlError.hpp>
#include <DlSystem/ITensor.hpp>
#include <DlSystem/ITensorFactory.hpp>
#include <DlSystem/IUserBuffer.hpp>
#include <DlSystem/IUserBufferFactory.hpp>
#include <string>
#include <sstream>
#include <iostream>
#include <fstream>
#include <array>

extern "C"{
  float run_model(float v_ego, float a_ego, float v_lead, float x_lead, float a_lead);
  void init_model();
  float run_model_lstm(float inputData[60]);
  float run_model_live_tracks(float inputData[62]);
}

struct testvar_t {
  float testvar;
};