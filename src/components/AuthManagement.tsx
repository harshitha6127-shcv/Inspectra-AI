import React, { useState } from "react";
import {
  Shield,
  Key,
  Users,
  CheckCircle2,
  XCircle,
  UserCheck,
  Lock,
  Unlock,
  AlertCircle
} from "lucide-react";

interface UserItem {
  id: number;
  username: string;
  email: string;
  role: "admin" | "operator";
  created_at: string;
}

const DEFAULT_USERS: UserItem[] = [
  { id: 1, username: "admin", email: "admin@factory.local", role: "admin", created_at: "2026-09-01 08:00:00" },
  { id: 2, username: "operator", email: "operator@factory.local", role: "operator", created_at: "2026-09-01 08:00:00" },
  { id: 3, username: "line_lead_sarah", email: "sarah.line1@factory.local", role: "operator", created_at: "2026-09-03 10:15:30" },
  { id: 4, username: "qc_director_chen", email: "chen.qc@factory.local", role: "admin", created_at: "2026-09-05 14:22:10" }
];

export function AuthManagement() {
  const [activeRole, setActiveRole] = useState<"admin" | "operator">("admin");
  const [users, setUsers] = useState<UserItem[]>(DEFAULT_USERS);
  const [newUsername, setNewUsername] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState<"admin" | "operator">("operator");
  const [feedback, setFeedback] = useState<string | null>(null);

  const handleCreateUser = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUsername || !newEmail || !newPassword) return;

    if (activeRole !== "admin") {
      alert("Permission Denied: Only Admin users can provision new accounts.");
      return;
    }

    const newUser: UserItem = {
      id: users.length + 1,
      username: newUsername.trim(),
      email: newEmail.trim(),
      role: newRole,
      created_at: new Date().toISOString().replace("T", " ").slice(0, 19)
    };

    setUsers([...users, newUser]);
    setNewUsername("");
    setNewEmail("");
    setNewPassword("");
    setFeedback(`Provisioned account for '${newUser.username}' as ${newUser.role.toUpperCase()}`);
    setTimeout(() => setFeedback(null), 4000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl bg-slate-900 border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-rose-400" />
            <h2 className="text-lg font-bold text-white">Prompt 13 — Authentication & Role-Based Access Control</h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Flask-Login session management · PBKDF2 password hashing · Role-gated endpoints
          </p>
        </div>

        {/* Active Role Simulation */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400">Simulate Session As:</span>
          <button
            onClick={() => setActiveRole("admin")}
            className={`px-3 py-1.5 rounded-lg font-bold border transition-all ${
              activeRole === "admin"
                ? "bg-rose-950/80 border-rose-600 text-rose-300"
                : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            Admin Session
          </button>
          <button
            onClick={() => setActiveRole("operator")}
            className={`px-3 py-1.5 rounded-lg font-bold border transition-all ${
              activeRole === "operator"
                ? "bg-emerald-950/80 border-emerald-600 text-emerald-300"
                : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            Operator Session
          </button>
        </div>
      </div>

      {feedback && (
        <div className="p-3 bg-emerald-950/70 border border-emerald-700/60 rounded-lg text-xs text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          <span>{feedback}</span>
        </div>
      )}

      {/* Permissions Matrix */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="text-sm font-bold text-white mb-1">Role Permission Matrix (Prompt 13)</h3>
        <p className="text-xs text-slate-400 mb-4">
          Enforced server-side via <code className="text-cyan-400 font-mono">@login_required</code> and{" "}
          <code className="text-rose-400 font-mono">@admin_required</code> decorators in <code className="text-emerald-400 font-mono">src/app.py</code>
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="bg-slate-950/80 text-slate-400 border-b border-slate-800 font-mono text-[11px] uppercase">
                <th className="py-2.5 px-4">Endpoint / Action</th>
                <th className="py-2.5 px-4">Operator Permission</th>
                <th className="py-2.5 px-4">Administrator Permission</th>
                <th className="py-2.5 px-4">Current Simulation State</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {[
                { action: "GET / (Batch Upload & Analyze)", op: true, admin: true },
                { action: "GET /scan (Dedicated Camera Scan)", op: true, admin: true },
                { action: "POST /analyze (Run Inspection Pipeline)", op: true, admin: true },
                { action: "GET /dashboard & /api/dashboard-data", op: true, admin: true },
                { action: "GET /export-csv (Download CSV records)", op: true, admin: true },
                { action: "POST /clear-history (Purge SQLite Database)", op: false, admin: true },
                { action: "POST /register (Provision New Accounts)", op: false, admin: true }
              ].map((row, idx) => {
                const isAllowed = activeRole === "admin" ? row.admin : row.op;
                return (
                  <tr key={idx} className="hover:bg-slate-800/30">
                    <td className="py-2.5 px-4 font-mono text-slate-200">{row.action}</td>
                    <td className="py-2.5 px-4">
                      {row.op ? (
                        <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Allowed
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-rose-400 font-semibold">
                          <XCircle className="w-3.5 h-3.5" /> 403 Forbidden
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-4">
                      <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Allowed
                      </span>
                    </td>
                    <td className="py-2.5 px-4">
                      {isAllowed ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-700">
                          AUTHORIZED
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-300 border border-rose-700">
                          BLOCKED (403)
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Users Table & Provisioning Form */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* User Account Registry */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Users className="w-4 h-4 text-cyan-400" />
                <span>Active User Accounts (SQLite users Table)</span>
              </h3>
              <p className="text-xs text-slate-400">Default accounts auto-seeded on first server startup</p>
            </div>
            <span className="text-xs font-mono bg-slate-950 px-2.5 py-1 rounded border border-slate-800 text-slate-300">
              {users.length} Users
            </span>
          </div>

          <div className="space-y-2.5">
            {users.map((u) => (
              <div
                key={u.id}
                className="p-3 bg-slate-950/70 border border-slate-800/80 rounded-lg flex items-center justify-between gap-3 text-xs"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ${
                    u.role === "admin" ? "bg-rose-950 text-rose-400 border border-rose-800" : "bg-emerald-950 text-emerald-400 border border-emerald-800"
                  }`}>
                    {u.username.slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <div className="font-bold text-white flex items-center gap-2">
                      <span>{u.username}</span>
                      <span className={`text-[10px] px-2 py-0.2 rounded font-bold border ${
                        u.role === "admin" ? "bg-rose-950 text-rose-300 border-rose-800" : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                      }`}>
                        {u.role.toUpperCase()}
                      </span>
                    </div>
                    <span className="text-slate-400 font-mono text-[11px]">{u.email}</span>
                  </div>
                </div>

                <div className="text-right font-mono text-[11px] text-slate-500">
                  <span>Created: {u.created_at.slice(0, 10)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Provision New Account Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-1">
            <UserCheck className="w-4 h-4 text-emerald-400" />
            <span>Provision User</span>
          </h3>
          <p className="text-xs text-slate-400 mb-4">
            {activeRole === "admin"
              ? "Administrator access granted."
              : "Disabled: Admin privileges required."}
          </p>

          <form onSubmit={handleCreateUser} className="space-y-3 text-xs">
            <div>
              <label className="block text-slate-400 font-medium mb-1">Username</label>
              <input
                type="text"
                disabled={activeRole !== "admin"}
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                placeholder="e.g. inspector_dave"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white outline-none disabled:opacity-50"
              />
            </div>

            <div>
              <label className="block text-slate-400 font-medium mb-1">Email</label>
              <input
                type="email"
                disabled={activeRole !== "admin"}
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                placeholder="dave@factory.local"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white outline-none disabled:opacity-50"
              />
            </div>

            <div>
              <label className="block text-slate-400 font-medium mb-1">Initial Password</label>
              <input
                type="password"
                disabled={activeRole !== "admin"}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Secure password"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white outline-none disabled:opacity-50"
              />
            </div>

            <div>
              <label className="block text-slate-400 font-medium mb-1">Assigned Role</label>
              <select
                disabled={activeRole !== "admin"}
                value={newRole}
                onChange={(e) => setNewRole(e.target.value as "admin" | "operator")}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white outline-none disabled:opacity-50"
              >
                <option value="operator">Operator (Inspection & Scan)</option>
                <option value="admin">Administrator (Full Access)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={activeRole !== "admin"}
              className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold text-xs transition-all mt-2 cursor-pointer"
            >
              Provision Account
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
