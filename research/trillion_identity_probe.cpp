// HingeZero 1T research: ZERO-STEP exact identity decoding with the original
// C++20 deterministic 128-bit synthetic pattern(id) representation.
// This is NOT a physical trillion-record memory bank or general ANN retrieval.
// The original HingeZero_Native_1B.cpp source remains unchanged.
#define main hingezero_original_entry
#include "../HingeZero_Native_1B.cpp"
#undef main
#include <optional>
#include <random>
constexpr uint64_t DOMAIN=1000000000000ULL;
constexpr uint64_t STEP=0x9E3779B97F4A7C15ULL;
constexpr uint64_t MULT1=0xBF58476D1CE4E5B9ULL;
constexpr uint64_t MULT2=0x94D049BB133111EBULL;
constexpr uint64_t ID_MULT=0xD1342543DE82EF95ULL;
constexpr uint64_t ALL=~uint64_t(0);

constexpr uint64_t mod_inverse(uint64_t a){
  uint64_t x=a;
  for(int i=0;i<6;++i)x*=2-a*x;
  return x;
}
static_assert(mod_inverse(MULT1)*MULT1==1);
static_assert(mod_inverse(MULT2)*MULT2==1);
static_assert(mod_inverse(ID_MULT)*ID_MULT==1);
uint64_t undo_xor(uint64_t y,int s){
  uint64_t x=y;
  for(int k=s;k<64;k*=2)x^=x>>k;
  return x;
}
uint64_t inverse_splitmix(uint64_t z){
  z=undo_xor(z,31);
  z*=mod_inverse(MULT2);
  z=undo_xor(z,27);
  z*=mod_inverse(MULT1);
  return undo_xor(z,30);
}
uint64_t from_half(uint64_t half,bool second){
  uint64_t original_seed=inverse_splitmix(half)-STEP*(second?2ULL:1ULL);
  return (original_seed^BASESEED)*mod_inverse(ID_MULT);
}
struct Cue {
  Pattern bits;
  Pattern known;
  unsigned tolerated_errors;
};
std::optional<uint64_t> lookup(const Cue& cue){
  // A full intact half of this *synthetic*, reversible code is required.
  // No record bank is scanned, and no iterative HingeZero steps are invoked.
  const bool lo=cue.known.lo==ALL,hi=cue.known.hi==ALL;
  if(!lo&&!hi)return std::nullopt;
  uint64_t candidate[2];int size=0;
  if(lo)candidate[size++]=from_half(cue.bits.lo,false);
  if(hi)candidate[size++]=from_half(cue.bits.hi,true);
  unsigned best=129;
  std::optional<uint64_t> result;
  for(int i=0;i<size;++i){
    uint64_t id=candidate[i];
    if(id>=DOMAIN)continue;
    Pattern actual=pattern(id); // Exact synthetic-state witness.
    unsigned errors=std::popcount((actual.lo^cue.bits.lo)&cue.known.lo)
                   +std::popcount((actual.hi^cue.bits.hi)&cue.known.hi);
    if(errors<=cue.tolerated_errors && errors<best){
      result=id;best=errors;
    }
  }
  return result;
}
struct CaseResult{
  std::string name;
  uint64_t total=0,correct=0,not_found=0,incorrect=0;
  double ms=0;
};
CaseResult run(const std::string& name,uint64_t count,uint64_t seed){
  std::mt19937_64 rng(seed);
  std::vector<uint64_t> expected;expected.reserve(count);
  std::vector<Cue> cues;cues.reserve(count);
  for(uint64_t i=0;i<count;++i){
    uint64_t id=rng()%DOMAIN;
    if(i==0)id=0;
    if(i==1)id=DOMAIN-1;
    if(i==2)id=417;
    if(i==3)id=777777777;
    Pattern p=pattern(id);
    Cue cue{p,{ALL,ALL},0};
    if(name=="erase_low_64"){cue.bits.lo=0;cue.known.lo=0;}
    if(name=="erase_high_64"){cue.bits.hi=0;cue.known.hi=0;}
    if(name=="flip_one_low"){cue.bits.lo^=1ULL<<(rng()%64);cue.tolerated_errors=1;}
    if(name=="flip_one_each"){cue.bits.lo^=1ULL<<(rng()%64);cue.bits.hi^=1ULL<<(rng()%64);cue.tolerated_errors=2;}
    if(name=="flip_20_percent"){
      std::array<uint8_t,128> positions{};
      for(int j=0;j<128;++j)positions[j]=uint8_t(j);
      for(int j=127;j>0;--j)std::swap(positions[j],positions[rng()%(j+1)]);
      for(int j=0;j<26;++j){
        const unsigned bit=positions[j];
        if(bit<64)cue.bits.lo^=1ULL<<bit;
        else cue.bits.hi^=1ULL<<(bit-64);
      }
      cue.tolerated_errors=26;
    }
    expected.push_back(id);cues.push_back(cue);
  }
  CaseResult result;result.name=name;result.total=count;
  auto start=Clock::now();
  for(uint64_t i=0;i<count;++i){
    auto id=lookup(cues[i]);
    if(!id)++result.not_found;
    else if(*id==expected[i])++result.correct;
    else ++result.incorrect;
  }
  result.ms=elapsed_ms(start);
  return result;
}
int main(int argc,char**argv){
  const uint64_t count=argc>1?std::stoull(argv[1]):250000;
  if(count<4||count>1000000){
    std::cerr<<"probe count must be from 4 to 1,000,000\n";return 2;
  }
  std::cout<<"{\"type\":\"scope\",\"virtual_identity_domain\":"<<DOMAIN
           <<",\"physically_stored_records\":0,\"refinement_steps\":0"
           <<",\"algorithm\":\"invertible deterministic synthetic ID mapping\""
           <<",\"not_a_trillion_record_memory_benchmark\":true}\n";
  bool passed=true;
  const std::vector<std::string> names={
    "exact","erase_low_64","erase_high_64","flip_one_low",
    "flip_one_each","flip_20_percent"
  };
  for(std::size_t i=0;i<names.size();++i){
    auto r=run(names[i],count,0xcafe53a1ULL+i*0x9e37ULL);
    std::cout<<std::setprecision(9)
      <<"{\"type\":\"measurement\",\"cue\":\""<<r.name
      <<"\",\"probes\":"<<r.total<<",\"correct\":"<<r.correct
      <<",\"incorrect\":"<<r.incorrect
      <<",\"not_found\":"<<r.not_found
      <<",\"elapsed_ms\":"<<r.ms
      <<",\"us_per_lookup\":"<<r.ms*1000.0/r.total
      <<",\"lookups_per_second\":"<<r.total*1000.0/r.ms<<"}\n";
    if(i<4&&r.correct!=count)passed=false;
  }
  return passed?0:1;
}
