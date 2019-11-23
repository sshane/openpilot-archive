using Cxx = import "./include/c++.capnp";
$Cxx.namespace("cereal");

using Java = import "./include/java.capnp";
$Java.package("ai.comma.openpilot.cereal");
$Java.outerClassname("smiskol");

@0xca61a35dedbd6328;

struct SmiskolStruct {
  stockGas @0 :Float32;
  sportOn @1 :Bool;
}


struct EventSmiskol {
  # in nanoseconds?
  logMonoTime @0 :UInt64;
  valid @6 :Bool = true;

  union {
    smiskolStruct @1 :SmiskolStruct;
  }
}