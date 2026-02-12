"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "../../lib/supabaseClient";

type Role = "USER" | "ADMIN";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 6;

interface RegisterFormProps {
  role: Role;
  redirectPath?: string;
  title?: string;
}

export function RegisterForm({
  role,
  redirectPath = "/",
  title,
}: RegisterFormProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [name, setName] = useState("");
  const [msg, setMsg] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const validate = (): string | null => {
    if (!email.trim()) return "メールアドレスを入力してください";
    if (!EMAIL_REGEX.test(email)) return "有効なメールアドレスを入力してください";
    if (!password) return "パスワードを入力してください";
    if (password.length < MIN_PASSWORD_LENGTH)
      return `パスワードは${MIN_PASSWORD_LENGTH}文字以上で入力してください`;
    if (password !== passwordConfirm) return "パスワードが一致しません";
    if (!name.trim()) return "表示名を入力してください";
    return null;
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg("");

    const validationError = validate();
    if (validationError) {
      setMsg(validationError);
      return;
    }

    setLoading(true);

    const { error } = await supabase.auth.signUp({
      email: email.trim(),
      password,
      options: {
        data: {
          display_name: name.trim(),
          role,
        },
      },
    });

    setLoading(false);

    if (error) {
      setMsg(`登録に失敗しました: ${error.message}`);
      return;
    }

    setMsg("登録が完了しました。リダイレクトしています...");
    router.push(redirectPath);
  };

  const displayTitle = title ?? (role === "ADMIN" ? "管理者登録" : "新規登録");

  return (
    <main className="p-6">
      <h1 className="text-xl font-bold mb-4">{displayTitle}</h1>

      <form onSubmit={onSubmit} className="grid gap-4 max-w-md">
        <div>
          <label htmlFor="email" className="block text-sm mb-1">
            メールアドレス
          </label>
          <input
            id="email"
            type="email"
            placeholder="email@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full p-2 border rounded"
            disabled={loading}
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm mb-1">
            パスワード
          </label>
          <input
            id="password"
            type="password"
            placeholder="6文字以上"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full p-2 border rounded"
            disabled={loading}
          />
        </div>

        <div>
          <label htmlFor="passwordConfirm" className="block text-sm mb-1">
            パスワード（確認）
          </label>
          <input
            id="passwordConfirm"
            type="password"
            placeholder="同じパスワードを入力"
            value={passwordConfirm}
            onChange={(e) => setPasswordConfirm(e.target.value)}
            className="w-full p-2 border rounded"
            disabled={loading}
          />
        </div>

        <div>
          <label htmlFor="name" className="block text-sm mb-1">
            表示名
          </label>
          <input
            id="name"
            type="text"
            placeholder="山田 太郎"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full p-2 border rounded"
            disabled={loading}
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="p-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "登録中..." : "登録"}
        </button>

        {msg && <p className="text-sm">{msg}</p>}

        <Link href="/login" className="text-blue-600 hover:underline text-sm">
          ログイン画面へ
        </Link>
      </form>
    </main>
  );
}
