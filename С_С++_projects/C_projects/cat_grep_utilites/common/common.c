#include "common.h"

void PrintUsage(const char* program_name);

void PrintUsage(const char* program_name) {
  fprintf(stderr, "Usage: %s [options] [arguments]\n", program_name);
}
