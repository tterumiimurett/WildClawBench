# Experiment Sessions

An experiment session is a bounded investigation whose decisions, specifications, evidence, tickets, and results share one declared purpose.

## Language

**Work Session**:
A named documentation boundary for one purpose across one conversation or a related series of conversations.
_Avoid_: Chat, thread, folder

**Session Binding**:
The recorded association between the current conversation and one Work Session directory.
_Avoid_: Current directory, active chat

**Experimental Condition**:
One controlled variant in a comparison, including its prompt source, model endpoint, harness, and repetition policy.
_Avoid_: Run type, version

**Clean Baseline**:
The condition using the original WildClawBench Markdown task prompt through the configured Azure evaluation endpoint.
_Avoid_: Original run, normal prompt

**Colloquial Condition**:
The paired condition that changes only the task prompt to Agentic ASR `colloquial_prompt` content.
_Avoid_: ASR run, modified prompt
