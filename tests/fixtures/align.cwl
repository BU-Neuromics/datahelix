#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool

label: "Stub alignment workflow for integration tests"
doc: |
  This CWL stub is never executed in tests — the CWL executor is always mocked.
  It exists only so that Canon's rule validation passes when loading rules from YAML.

baseCommand: echo

inputs:
  sample_id:
    type: string

outputs:
  aligned_bam:
    type: File
    outputBinding:
      glob: "*.bam"
