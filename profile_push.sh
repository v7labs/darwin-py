#!/usr/bin/env bash
TIMESTAMP=`date '+%s'`
OUTPUT_PROFILE_FILE="output_profile_$TIMESTAMP.out"
OUTPUT_STDOUT_FILE="output_stdout_$TIMESTAMP.out"
OUTPUT_TIME_FILE="output_time_$TIMESTAMP.out"

echo "Running darwin push profile script"
echo "Output file: $OUTPUT_PROFILE_FILE"
echo 
echo

echo "Deleting any old test datasets, and creating new one for testing"
.venv/bin/python -m darwin.cli dataset remove test_large_data_owen
.venv/bin/python -m darwin.cli dataset create test_large_data_owen


echo "Running the profiler"


echo "Running profile on push command.  This will take a while..."

gtime -o push_$OUTPUT_TIME_FILE .venv/bin/python -m cProfile -o push_$OUTPUT_PROFILE_FILE -m darwin.cli dataset push test_large_data_owen ~/.darwin/datasets/rafals-team/import_benchmark/>push_$OUTPUT_STDOUT_FILE
gtime -o import_$OUTPUT_TIME_FILE .venv/bin/python -m cProfile -o import_$OUTPUT_PROFILE_FILE -m darwin.cli dataset import test_large_data_owen darwin ~/.darwin/datasets/rafals-team/import_benchmark/>import_$OUTPUT_STDOUT_FILE


echo "Done."
echo
echo "Profile file: $OUTPUT_PROFILE_FILE"
echo "Stdout file: $OUTPUT_STDOUT_FILE"
