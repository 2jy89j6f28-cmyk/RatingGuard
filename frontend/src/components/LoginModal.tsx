"use client";

import { useState, useCallback, type FormEvent } from "react";
import { useAuth } from "@/hooks/useAuth";

/* ═══════════════════════════════════════════════════════════════
   LoginModal —— 登录/注册模态弹窗
   ═══════════════════════════════════════════════════════════════ */

type Tab = "login" | "register";

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function LoginModal({ isOpen, onClose }: LoginModalProps) {
  const { login, register } = useAuth();
  const [tab, setTab] = useState<Tab>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const resetForm = useCallback(() => {
    setUsername("");
    setPassword("");
    setError("");
    setLoading(false);
  }, []);

  const handleTabSwitch = useCallback(
    (newTab: Tab) => {
      setTab(newTab);
      resetForm();
    },
    [resetForm]
  );

  const handleClose = useCallback(() => {
    resetForm();
    setTab("login");
    onClose();
  }, [onClose, resetForm]);

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setError("");

      if (!username.trim() || !password.trim()) {
        setError("请填写用户名和密码");
        return;
      }

      setLoading(true);
      try {
        if (tab === "login") {
          await login(username.trim(), password);
        } else {
          await register(username.trim(), password);
        }
        handleClose();
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "操作失败");
      } finally {
        setLoading(false);
      }
    },
    [tab, username, password, login, register, handleClose]
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 遮罩层 */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* 弹窗 */}
      <div className="relative w-full max-w-sm rounded-2xl border border-gray-800 bg-gray-950 p-6 shadow-2xl shadow-black/50 animate-fade-in">
        {/* 标签切换 */}
        <div className="mb-5 flex rounded-lg border border-gray-800 bg-gray-900/50 p-0.5">
          <button
            type="button"
            onClick={() => handleTabSwitch("login")}
            className={`flex-1 rounded-md py-2 text-sm font-medium transition-all ${
              tab === "login"
                ? "bg-gray-800 text-gray-200 shadow-sm"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            登录
          </button>
          <button
            type="button"
            onClick={() => handleTabSwitch("register")}
            className={`flex-1 rounded-md py-2 text-sm font-medium transition-all ${
              tab === "register"
                ? "bg-gray-800 text-gray-200 shadow-sm"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            注册
          </button>
        </div>

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs text-gray-500">用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="输入用户名"
              autoComplete="username"
              className="w-full rounded-lg border border-gray-800 bg-gray-900/50 px-3.5 py-2.5 text-sm text-gray-200 placeholder-gray-600 outline-none transition-colors focus:border-accent/50 focus:bg-gray-900"
              disabled={loading}
            />
          </div>

          <div>
            <label className="mb-1 block text-xs text-gray-500">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="输入密码"
              autoComplete={tab === "login" ? "current-password" : "new-password"}
              className="w-full rounded-lg border border-gray-800 bg-gray-900/50 px-3.5 py-2.5 text-sm text-gray-200 placeholder-gray-600 outline-none transition-colors focus:border-accent/50 focus:bg-gray-900"
              disabled={loading}
            />
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-3.5 py-2.5 text-sm text-red-400">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-glow w-full rounded-lg border border-accent/40 bg-accent/10 px-4 py-2.5 text-sm font-medium text-accent-light transition-all duration-200 hover:bg-accent/20 hover:shadow-[0_0_20px_-8px_rgba(16,185,129,0.3)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-gray-600 border-t-accent" />
                处理中…
              </span>
            ) : tab === "login" ? (
              "登录"
            ) : (
              "注册"
            )}
          </button>
        </form>

        {/* 关闭按钮 */}
        <button
          type="button"
          onClick={handleClose}
          className="absolute right-3 top-3 rounded-lg p-1 text-gray-600 transition-colors hover:bg-gray-800 hover:text-gray-300"
          aria-label="关闭"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
