'use client';

import {
  ArtifactCreatedEvent,
  RunCompletedEvent,
  RunFailedEvent,
  RunStartedEvent,
  StepEvent,
  TaskRunEvent,
  ToolCallEvent,
  ToolResultEvent,
} from '../types';
import { ToolCallItem } from './ToolCallItem';

interface ExecutionTimelineProps {
  events: TaskRunEvent[];
}

export function ExecutionTimeline({ events }: ExecutionTimelineProps) {
  const runStarted = events.find((e): e is RunStartedEvent => e.type === 'run_started');
  const runCompleted = events.find((e): e is RunCompletedEvent => e.type === 'run_completed');
  const runFailed = events.find((e): e is RunFailedEvent => e.type === 'run_failed');
  const toolCalls = events.filter((e): e is ToolCallEvent => e.type === 'tool_call');
  const toolResults = events.filter((e): e is ToolResultEvent => e.type === 'tool_result');
  const steps = events.filter((e): e is StepEvent => e.type === 'step');
  const artifacts = events.filter((e): e is ArtifactCreatedEvent => e.type === 'artifact_created');

  return (
    <div className="space-y-4">
      {(runStarted || runCompleted || runFailed) && (
        <div className="rounded-lg border border-gray-200 p-3 text-sm text-gray-700 space-y-1">
          {runStarted && <p>Run started.</p>}
          {runCompleted && <p>Run completed.</p>}
          {runFailed && <p className="text-red-700">Run failed: {runFailed.error || 'unknown error'}</p>}
        </div>
      )}

      {steps.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Execution Steps</h3>
          <div className="space-y-2">
            {steps.map((step, idx) => (
              <div key={idx} className="flex gap-2 text-sm">
                <span className="text-gray-400">{step.iteration || idx + 1}.</span>
                <span className="text-gray-700">{step.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {toolCalls.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Tool Calls</h3>
          <div className="space-y-3">
            {toolCalls.map((call, idx) => {
              const callName = call.tool_name || call.tool;
              const result = toolResults.find((r) => {
                const resultName = r.tool_name || r.tool;
                return callName && resultName ? resultName === callName : false;
              });
              return <ToolCallItem key={idx} toolCall={call} result={result} />;
            })}
          </div>
        </div>
      )}

      {artifacts.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Artifacts</h3>
          <div className="space-y-2">
            {artifacts.map((artifact, idx) => (
              <div key={idx} className="rounded-lg border border-gray-200 p-3 text-sm text-gray-700">
                {artifact.name || 'Artifact created'}
              </div>
            ))}
          </div>
        </div>
      )}

      {events.length === 0 && (
        <p className="text-sm text-gray-500 text-center py-8">
          Waiting for execution to start...
        </p>
      )}
    </div>
  );
}
