'use client';

import { TaskRunEvent, ToolCallEvent, ToolResultEvent, StepEvent } from '../types';
import { ToolCallItem } from './ToolCallItem';

interface ExecutionTimelineProps {
  events: TaskRunEvent[];
}

export function ExecutionTimeline({ events }: ExecutionTimelineProps) {
  const toolCalls = events.filter((e): e is ToolCallEvent => e.type === 'tool_call');
  const toolResults = events.filter((e): e is ToolResultEvent => e.type === 'tool_result');
  const steps = events.filter((e): e is StepEvent => e.type === 'step');

  return (
    <div className="space-y-4">
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
              const result = toolResults.find(r => r.tool_name === call.tool_name);
              return <ToolCallItem key={idx} toolCall={call} result={result} />;
            })}
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
