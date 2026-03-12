'use client';

import { ToolCallEvent, ToolResultEvent } from '../types';

interface ToolCallItemProps {
  toolCall: ToolCallEvent;
  result?: ToolResultEvent;
}

export function ToolCallItem({ toolCall, result }: ToolCallItemProps) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
      <div className="flex items-center gap-2 mb-2">
        <span className="font-mono text-sm font-semibold text-blue-600">
          {toolCall.tool_name}
        </span>
        {result && (
          <span className={`text-xs px-2 py-0.5 rounded ${
            result.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
            {result.success ? 'Success' : 'Failed'}
          </span>
        )}
      </div>

      {Object.keys(toolCall.arguments).length > 0 && (
        <div className="mb-2">
          <p className="text-xs text-gray-500 mb-1">Arguments:</p>
          <pre className="text-xs bg-white p-2 rounded border border-gray-200 overflow-x-auto">
            {JSON.stringify(toolCall.arguments, null, 2)}
          </pre>
        </div>
      )}

      {result && (
        <div>
          <p className="text-xs text-gray-500 mb-1">Result:</p>
          <pre className="text-xs bg-white p-2 rounded border border-gray-200 overflow-x-auto">
            {result.success ? result.output : result.error}
          </pre>
        </div>
      )}
    </div>
  );
}
