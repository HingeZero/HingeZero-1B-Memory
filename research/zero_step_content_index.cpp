// Research benchmark: genuine content-addressed associative retrieval.
// A random memory must physically exist in the stored corpus before it can be returned.
// Query inputs carry only (possibly corrupted or masked) 128-bit content, never an ID.
// No reversible-id lookup. No HingeZero iterative refinement (zero steps).
// Candidate generation is standard multi-index hashing (8 x 16-bit blocks).
// This is not a claim of a trillion physically stored memories or novel ANN indexing.
#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;
using Clock=chrono::steady_clock;
struct Pattern{uint64_t lo,hi;};
static_assert(sizeof(Pattern)==16);
static uint64_t splitmix(uint64_t& x){
  x+=0x9E3779B97F4A7C15ULL;
  auto z=x;
  z=(z^(z>>30))*0xBF58476D1CE4E5B9ULL;
  z=(z^(z>>27))*0x94D049BB133111EBULL;
  return z^(z>>31);
}
static double millis(Clock::time_point t){
  return chrono::duration<double,milli>(Clock::now()-t).count();
}
static uint16_t bandkey(Pattern p,int band){
  uint64_t word=band<4?p.lo:p.hi;
  return uint16_t((word>>(16*(band%4)))&0xffffULL);
}
struct Query{Pattern bits,known;int radius;};
struct Index{
  vector<Pattern> records;
  array<vector<uint32_t>,8> begin,ids;
  vector<uint8_t> marks;
  uint8_t generation=0;
  string path;
  double build_ms=0;
  explicit Index(uint32_t n,string output):path(std::move(output)){
    auto t=Clock::now();
    records.resize(n);
    uint64_t state=0x5eedeed493c6beefULL;
    // One sequential PRNG produces independent stored words, not pattern(ID).
    for(uint32_t i=0;i<n;++i)records[i]={splitmix(state),splitmix(state)};
    {
      ofstream out(path,ios::binary|ios::trunc);
      if(!out)throw runtime_error("unable to create physical bank");
      out.write(reinterpret_cast<char const*>(records.data()),streamsize(n)*16);
      out.flush();
      if(!out)throw runtime_error("failed physical bank write");
    }
    for(int b=0;b<8;b++)begin[b].assign(65537,0);
    for(auto p:records){
      for(int b=0;b<8;b++)++begin[b][1+bandkey(p,b)];
    }
    for(int b=0;b<8;b++){
      for(int k=1;k<=65536;k++)begin[b][k]+=begin[b][k-1];
      ids[b].resize(n);
    }
    auto cursors=begin;
    for(uint32_t i=0;i<n;i++){
      auto p=records[i];
      for(int b=0;b<8;b++)ids[b][cursors[b][bandkey(p,b)]++]=i;
    }
    marks.assign(n,0);
    build_ms=millis(t);
  }
  struct Answer{
    bool found=false;
    bool abstained=false;
    uint32_t id=0;
    unsigned errors=129;
    uint64_t inspected=0;
    double search_ms=0;
    bool witness=false;
  };
  Answer search(Query q,uint64_t cap=12000000){
    auto t=Clock::now();
    Answer a{};
    unsigned known_bits=popcount(q.known.lo)+popcount(q.known.hi);
    // No justifiable unique identity among very large random corpora with 8 known bits.
    if(known_bits<32){a.abstained=true;a.search_ms=millis(t);return a;}
    if(++generation==0){fill(marks.begin(),marks.end(),0);generation=1;}
    const uint8_t tag=generation;
    for(int b=0;b<8;b++){
      uint16_t key=bandkey(q.bits,b);
      uint16_t mask=bandkey(q.known,b);
      for(int k=0;k<65536;k++){
        if(popcount(uint16_t((uint16_t(k)^key)&mask))>q.radius)continue;
        const auto from=begin[b][k],to=begin[b][k+1];
        for(uint32_t j=from;j<to;j++){
          uint32_t id=ids[b][j];
          if(marks[id]==tag)continue;
          marks[id]=tag;
          ++a.inspected;
          if(a.inspected>cap){
            a.abstained=true;a.found=false;a.search_ms=millis(t);return a;
          }
          auto p=records[id];
          unsigned errors=popcount((p.lo^q.bits.lo)&q.known.lo)
                        +popcount((p.hi^q.bits.hi)&q.known.hi);
          if(!a.found||errors<a.errors||(errors==a.errors&&id<a.id)){
            a.id=id;a.errors=errors;a.found=true;
          }
        }
      }
    }
    a.search_ms=millis(t);
    // Read the selected memory independently from the actual physical bank.
    // This witnesses stored-state membership, not desired identity correctness.
    if(a.found){
      ifstream in(path,ios::binary);
      in.seekg(streamoff(a.id)*16);
      Pattern persisted{};
      in.read(reinterpret_cast<char*>(&persisted),16);
      a.witness=bool(in)&&memcmp(&persisted,&records[a.id],16)==0;
    }
    return a;
  }
};
static Query make_query(Pattern p,string regime,uint64_t seed){
  Query q{p,{~0ULL,~0ULL},0};
  if(regime=="exact")return q;
  array<int,128> positions{};
  iota(positions.begin(),positions.end(),0);
  mt19937_64 rng(seed);
  shuffle(positions.begin(),positions.end(),rng);
  auto flip=[&](int j){
    int bit=positions[j];
    if(bit<64)q.bits.lo^=1ULL<<bit;
    else q.bits.hi^=1ULL<<(bit-64);
  };
  auto erase=[&](int j){
    int bit=positions[j];
    if(bit<64){q.known.lo&=~(1ULL<<bit);q.bits.lo&=~(1ULL<<bit);}
    else {bit-=64;q.known.hi&=~(1ULL<<bit);q.bits.hi&=~(1ULL<<bit);}
  };
  if(regime=="flip20"){for(int j=0;j<26;j++)flip(j);q.radius=2;}
  else if(regime=="flip35"){for(int j=0;j<45;j++)flip(j);q.radius=3;}
  else if(regime=="missing50"){for(int j=0;j<64;j++)erase(j);}
  else if(regime=="eight_known"){for(int j=0;j<120;j++)erase(j);}
  else throw runtime_error("bad regime");
  return q;
}
int main(int argc,char**argv){
  try{
    if(argc!=3)throw runtime_error("usage: hz_associative COUNT BANK_FILE");
    uint64_t total=stoull(argv[1]);
    if(total<1000||total>100000000)throw runtime_error("count out of safe benchmark range");
    if(total>numeric_limits<uint32_t>::max())throw runtime_error("uint32 ID limit");
    Index index(uint32_t(total),argv[2]);
    cout<<setprecision(8)
      <<"{\"type\":\"setup\",\"physical_memories\":"<<total
      <<",\"bytes\":"<<total*16
      <<",\"steps\":0,\"candidate_method\":\"8-band 16-bit multi-index hashing\""
      <<",\"inverse_id_lookup\":false,\"build_ms\":"<<index.build_ms<<"}\n";
    vector<string> regimes={"exact","flip20","flip35","missing50","eight_known"};
    vector<uint32_t> targets={417u,uint32_t(total-1)};
    unsigned failures=0;
    for(auto const& regime:regimes){
      for(auto target:targets){
        Query q=make_query(index.records[target],regime,target*131ULL+total);
        auto a=index.search(q);
        bool correct=a.found&&a.id==target;
        if(!a.abstained&&!a.witness)++failures;
        if(regime=="exact"&&!correct)++failures;
        cout<<"{\"type\":\"query\",\"physical_memories\":"<<total
            <<",\"cue\":\""<<regime<<"\",\"target\":"<<target
            <<",\"found\":"<<(a.found?"true":"false")
            <<",\"selected\":"<<(a.found?to_string(a.id):"null")
            <<",\"correct\":"<<(correct?"true":"false")
            <<",\"witness\":"<<(a.witness?"true":"false")
            <<",\"abstained\":"<<(a.abstained?"true":"false")
            <<",\"candidate_inspections\":"<<a.inspected
            <<",\"search_ms\":"<<a.search_ms<<"}\n";
      }
    }
    return failures?1:0;
  }catch(exception const& e){cerr<<"ERROR: "<<e.what()<<"\n";return 1;}
}
