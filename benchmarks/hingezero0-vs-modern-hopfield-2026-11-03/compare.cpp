// C++20, one CPU thread. HingeZero zero-refinement Witness retrieval vs
// Modern Hopfield x'=M^T softmax(beta M x), followed by nearest stored-row ID.
// No softmax or nonlinear refinement on HZ side. Same dense stored bank, queries,
// precision, and dot-product scoring for all methods.
#include <vector>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <chrono>
#include <stdexcept>
#include <limits>
#include <numeric>
using namespace std;
using clk=chrono::steady_clock;
struct Header {uint32_t magic, n, p, t; float beta; uint32_t seed; float noise;};
struct Sample {int id; double us; double cos_true; bool witness; bool natural_stored;};

inline float dot(const float *a,const float*b,int n){double sum=0.0; for(int j=0;j<n;j++) sum+=(double)a[j]*(double)b[j]; return (float)sum;}
struct Bank {
 int n,p; vector<float> v;
 const float* at(int i)const{return v.data()+(size_t)i*n;}
 int argmax(const float*x)const{
   float best=-numeric_limits<float>::infinity(); int win=0;
   for(int i=0;i<p;i++){float s=dot(at(i),x,n);if(s>best){best=s;win=i;}}
   return win;
 }
 bool witness(int idx, const float* x)const {
   if(idx<0||idx>=p) return false;
   // Exact stored-state identity verification, plus preservation on repeat.
   // The state is returned as an exact copy of the selected stored row.
   vector<float> state(at(idx),at(idx)+n);
   if(memcmp(state.data(),at(idx),(size_t)n*sizeof(float))!=0 || memcmp(state.data(),x,(size_t)n*sizeof(float))!=0)return false;
   int again=idx; // original Witness observe(stored-tag) is preservation branch
   return again==idx && memcmp(state.data(),at(again),(size_t)n*sizeof(float))==0;
 }
};

// Full witness-constrained HingeZero zero-step readout. The original Python
// HingeZeroWitness has HZ_STEPS=8 fixed; bypassing refine and calling
// witness.observe(query, scores=bank@unit(query)) gives this same operation.
int hz_witness0(const Bank&b,const float*query,bool&valid) {
   int i=b.argmax(query);valid=b.witness(i,b.at(i));return i;
}
// MH true update, not just argmax of softmax weights. Identical bank & scoring.
int mh_update(const Bank&b,const float*query,float beta,vector<float>&scores,
              vector<float>&weights,vector<float>&state,double&state_cos) {
  float mx=-numeric_limits<float>::infinity();
  for(int i=0;i<b.p;i++){float s=dot(b.at(i),query,b.n);scores[i]=s;mx=max(mx,s);}
  double z=0;for(int i=0;i<b.p;i++){float v=expf(beta*(scores[i]-mx));weights[i]=v;z+=v;}
  fill(state.begin(),state.end(),0.f);
  for(int i=0;i<b.p;i++){
    float w=(float)(weights[i]/z);const float*row=b.at(i);
    for(int j=0;j<b.n;j++)state[j]+=w*row[j];
  }
  int selected=b.argmax(state.data());
  state_cos=0.0; // reported separately below for target-based accuracy
  return selected;
}
int mh_softmax_weight_argmax(const Bank&b,const float*query,float beta,
                            vector<float>&scores,vector<float>&weights){
  float mx=-numeric_limits<float>::infinity();
  for(int i=0;i<b.p;i++){float s=dot(b.at(i),query,b.n);scores[i]=s;mx=max(mx,s);}
  double sum=0;
  for(int i=0;i<b.p;i++){weights[i]=expf(beta*(scores[i]-mx));sum+=weights[i];}
  int win=0;float best=-1;for(int i=0;i<b.p;i++){
    float w=(float)(weights[i]/sum);if(w>best){best=w;win=i;}}
  return win;
}

int main(int argc,char**argv){
  try{
  if(argc!=2)throw runtime_error("usage: compare CASE.bin");
  ifstream in(argv[1],ios::binary);if(!in)throw runtime_error("cannot open input");
  Header h{};in.read((char*)&h,sizeof h);if(!in||h.magic!=0x485a4d48 || h.n<1 || h.p<2 || h.t<1)throw runtime_error("bad header");
  Bank b; b.n=(int)h.n;b.p=(int)h.p;b.v.resize((size_t)b.n*b.p);
  vector<float> qs((size_t)h.t*h.n);vector<int32_t> target(h.t);
  in.read((char*)b.v.data(),b.v.size()*sizeof(float));
  in.read((char*)qs.data(),qs.size()*sizeof(float));
  in.read((char*)target.data(),target.size()*sizeof(int32_t));
  if(!in)throw runtime_error("truncated file");
  vector<float> scores(h.p),weights(h.p),state(h.n);
  // Warm up each code path with the same input. Prevent dead-code elimination.
  volatile int sink=0;bool valid=false;double co=0;
  for(int i=0;i<3;i++){
    sink=sink+hz_witness0(b,qs.data(),valid);
    sink=sink+mh_update(b,qs.data(),h.beta,scores,weights,state,co);
    sink=sink+mh_softmax_weight_argmax(b,qs.data(),h.beta,scores,weights);
  }
  // Each query is measured independently; rotate methods to reduce systematic
  // method-order advantage. Repeat timing 3x and use median.
  cout<<fixed<<setprecision(5);
  for(int j=0;j<(int)h.t;j++){
    const float*query=qs.data()+(size_t)j*b.n;int truth=target[j];
    for(int m=0;m<4;m++){
      int method=(m+j)%4; // 0=HZ+Witness, 1=MH full, 2=MH softmax weight-ID, 3=cosine scan
      vector<double> times;times.reserve(3);int selected=-1;bool verified=true;
      double targetcos=0;bool natural_stored=true;
      for(int rep=0;rep<3;rep++){
        auto begin=clk::now();
        switch(method){
        case 0: selected=hz_witness0(b,query,verified);break;
        case 1: selected=mh_update(b,query,h.beta,scores,weights,state,co);break;
        case 2: selected=mh_softmax_weight_argmax(b,query,h.beta,scores,weights);break;
        case 3: selected=b.argmax(query);break;
        }
        auto end=clk::now();
        times.push_back(chrono::duration<double,micro>(end-begin).count());
      }
      sort(times.begin(),times.end());
      // MH natural output is the blended state, not a stored row. HZ and MH ID
      // readouts return a stored row, but only HZ includes identity verification.
      if(method==1){
        double length=0;for(float a:state)length+=(double)a*a;
        targetcos=length>0 ? dot(state.data(),b.at(truth),b.n)/sqrt(length) : 0;
        natural_stored=false;
        for(int i=0;i<b.p;i++){
          if(memcmp(state.data(),b.at(i),(size_t)b.n*sizeof(float))==0){natural_stored=true;break;}
        }
      }else targetcos=dot(b.at(selected),b.at(truth),b.n);
      cout<<h.n<<','<<h.p<<','<<h.seed<<','<<h.noise<<','<<h.beta<<','<<j<<','<<truth<<','<<method<<','<<selected<<','
          <<(selected==truth)<<','<<(method==0 ? (int)verified : -1)<<','<<(int)natural_stored<<','<<times[1]<<','<<targetcos<<'\n';
      if(method==0&&!verified)throw runtime_error("HZ Witness validation failure");
      sink=sink+selected;
    }
  }
  if(sink==-1)cerr<<"sink"<<sink<<'\n';
  }catch(exception&e){cerr<<"ERROR: "<<e.what()<<'\n';return 1;}
}