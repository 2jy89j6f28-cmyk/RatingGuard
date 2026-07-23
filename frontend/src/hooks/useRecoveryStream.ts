"use client";

import { useState, useRef, useCallback } from "react";

/* ═══════════════════════════════════════════════════════════
   SSE 流式 Hook 类型定义
   ═══════════════════════════════════════════════════════════ */

export interface StreamParams {
  review_text: string;
  country_code: string;
  customer_name: string;
  review_id?: number;
}

export interface StreamResult {
  reason_category: string;
  anger_level: number;
  customer_persona: {
    communication_style: string;
    cultural_traits: string;
    suggested_approach: string;
  };
  recovery_email: {
    subject: string;
    body: string;
    language: string;
  };
  rawText?: string;
}

interface SSEEvent {
  type: "token" | "done" | "error";
  content?: string;
  result?: StreamResult;
  message?: string;
}

interface UseRecoveryStreamReturn {
  /** 是否正在流式接收中 */
  isStreaming: boolean;
  /** 累积的文本（打字机效果用） */
  streamedText: string;
  /** 分析完成后的结构化结果 */
  result: StreamResult | null;
  /** 错误消息 */
  error: string | null;
  /** 启动流式分析 */
  startStream: (params: StreamParams) => Promise<void>;
  /** 重置状态 */
  reset: () => void;
}

/* ═══════════════════════════════════════════════════════════
   SSE 流式 Hook
   ═══════════════════════════════════════════════════════════ */

export function useRecoveryStream(): UseRecoveryStreamReturn {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedText, setStreamedText] = useState("");
  const [result, setResult] = useState<StreamResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 用 ref 累积文本，避免闭包陷阱
  const bufferRef = useRef("");
  const abortRef = useRef<AbortController | null>(null);

  const startStream = useCallback(async (params: StreamParams) => {
    // 取消之前的请求
    abortRef.current?.abort();
    const abort = new AbortController();
    abortRef.current = abort;

    // 重置状态
    setIsStreaming(true);
    setStreamedText("");
    setResult(null);
    setError(null);
    bufferRef.current = "";

    try {
      const response = await fetch("/api/stream-recovery", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
        signal: abort.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let sseBuffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        sseBuffer += decoder.decode(value, { stream: true });

        // 从 buffer 中提取完整的 SSE 事件
        const events = extractSSEEvents(sseBuffer);
        sseBuffer = events.remaining;

        for (const evt of events.parsed) {
          switch (evt.type) {
            case "token":
              bufferRef.current += evt.content || "";
              setStreamedText(bufferRef.current);
              break;
            case "done": {
              // 后端 done 事件字段在顶层，不在 result 嵌套里
              const event = evt as Record<string, unknown>;
              if (event.reason_category !== undefined) {
                const doneResult: StreamResult = {
                  reason_category: event.reason_category as string,
                  anger_level: event.anger_level as number,
                  customer_persona: event.customer_persona as StreamResult["customer_persona"],
                  recovery_email: event.recovery_email as StreamResult["recovery_email"],
                  rawText: event.rawText as string | undefined,
                };
                if (!bufferRef.current && doneResult.rawText) {
                  bufferRef.current = doneResult.rawText;
                  setStreamedText(bufferRef.current);
                }
                setResult(doneResult);
              }
              break;
            }
            case "error":
              setError(evt.message || "未知错误");
              break;
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : "请求失败");
    } finally {
      if (!abort.signal.aborted) {
        setIsStreaming(false);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
    setStreamedText("");
    setResult(null);
    setError(null);
    bufferRef.current = "";
  }, []);

  return { isStreaming, streamedText, result, error, startStream, reset };
}

/* ═══════════════════════════════════════════════════════════
  SSE 协议解析（处理分片到达的不完整事件）
  ═══════════════════════════════════════════════════════════ */

function extractSSEEvents(buffer: string): {
  parsed: SSEEvent[];
  remaining: string;
} {
  const parsed: SSEEvent[] = [];
  const parts = buffer.split("\n\n");

  // 最后一个元素可能是不完整的（还没有收到 \n\n），保留到下次
  const remaining = parts.pop() || "";

  for (const block of parts) {
    const trimmed = block.trim();
    if (!trimmed) continue;

    // 提取 data: 后的 JSON
    const dataMatch = trimmed.match(/^data:\s*(.+)$/m);
    if (!dataMatch) continue;

    try {
      const raw = JSON.parse(dataMatch[1]);
      parsed.push(raw as SSEEvent);
    } catch {
      // 忽略无法解析的残缺 JSON
    }
  }

  return { parsed, remaining };
}
