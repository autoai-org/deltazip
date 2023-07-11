/*
 * Copyright (c) 2020, NVIDIA CORPORATION. All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *  * Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *  * Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *  * Neither the name of NVIDIA CORPORATION nor the names of its
 *    contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND ANY
 * EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
 * CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 * EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
 * PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
 * PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
 * OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include "benchmark_template_chunked.cuh"
#include "nvcomp/gdeflate.h"

static nvcompBatchedGdeflateOpts_t nvcompBatchedGdeflateOpts = {0};

static bool handleCommandLineArgument(
    const std::string& arg,
    const char* const* additionalArgs,
    size_t& additionalArgsUsed)
{
  if (arg == "--algorithm" || arg == "-a") {
    int algorithm_type = atoi(*additionalArgs);
    additionalArgsUsed = 1;
    if (algorithm_type < 0 || algorithm_type > 2) {
      std::cerr << "ERROR: Gdeflate algorithm must be 0, 1, or 2, but it is "
                << algorithm_type << std::endl;
      return false;
    }
    nvcompBatchedGdeflateOpts.algo = algorithm_type;
    return true;
  }
  return false;
}

static bool isGdeflateInputValid(const std::vector<std::vector<char>>& data)
{
  for (const auto& chunk : data) {
    if (chunk.size() > 65536) {
      std::cerr << "ERROR: Gdeflate doesn't support chunk sizes larger than "
                   "65536 bytes."
                << std::endl;
      return false;
    }
  }

  return true;
}

void run_benchmark(
    const std::vector<std::vector<char>>& data,
    const bool warmup,
    const size_t count,
    const bool csv_output,
    const bool tab_separator,
    const size_t duplicate_count,
    const size_t num_files)
{
  run_benchmark_template(
      nvcompBatchedGdeflateCompressGetTempSize,
      nvcompBatchedGdeflateCompressGetMaxOutputChunkSize,
      nvcompBatchedGdeflateCompressAsync,
      nvcompBatchedGdeflateDecompressGetTempSize,
      nvcompBatchedGdeflateDecompressAsync,
      isGdeflateInputValid,
      nvcompBatchedGdeflateOpts,
      data,
      warmup,
      count,
      csv_output,
      tab_separator,
      duplicate_count,
      num_files);
}