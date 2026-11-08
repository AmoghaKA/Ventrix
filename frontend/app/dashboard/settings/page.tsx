"use client";

import { useEffect, useRef, useState, type ChangeEvent, type FormEvent, type ReactNode } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  getSystemStatus,
  getSystemUsage,
  getProfile,
  updateProfile,
  type SystemStatus,
  type SystemUsage,
  type UserProfile,
} from "@/lib/api";
import { supabase } from "@/lib/supabase";
import {
  Bell,
  Building2,
  Check,
  ChevronRight,
  Copy,
  CreditCard,
  Globe2,
  KeyRound,
  Lock,
  Mail,
  Monitor,
  Palette,
  Plug,
  RefreshCw,
  Save,
  Settings2,
  Shield,
  SlidersHorizontal,
  Trash2,
  UserCircle2,
  Workflow,
} from "lucide-react";

type SectionKey =
  | "profile"
  | "account"
  | "preferences"
  | "notifications"
  | "security"
  | "integrations"
  | "usage"
  | "danger";

const sections: { key: SectionKey; label: string; icon: typeof UserCircle2 }[] = [
  { key: "profile", label: "Profile", icon: UserCircle2 },
  { key: "account", label: "Account", icon: Mail },
  { key: "preferences", label: "Preferences", icon: SlidersHorizontal },
  { key: "notifications", label: "Notifications", icon: Bell },
  { key: "security", label: "Security", icon: Shield },
  { key: "integrations", label: "Integrations", icon: Plug },
  { key: "usage", label: "Usage & billing", icon: CreditCard },
  { key: "danger", label: "Danger zone", icon: Trash2 },
];

function Switch({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60 ${
        checked ? "bg-blue-600" : "bg-slate-200"
      }`}
    >
      <span
        className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform duration-200 ${
          checked ? "translate-x-5" : "translate-x-0.5"
        }`}
      />
    </button>
  );
}

function SectionCard({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <Card className="overflow-hidden p-0">
      <div className="border-b border-slate-100 px-6 py-5">
        <h2 className="text-base font-semibold tracking-tight text-slate-900">
          {title}
        </h2>
        {description && (
          <p className="mt-1 text-sm text-slate-500">{description}</p>
        )}
      </div>
      <div className="px-6 py-6">{children}</div>
      {footer && (
        <div className="flex items-center justify-end gap-3 border-t border-slate-100 bg-slate-50/60 px-6 py-4">
          {footer}
        </div>
      )}
    </Card>
  );
}

function FieldRow({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-[220px_1fr] sm:items-start sm:gap-6">
      <div>
        <p className="text-sm font-medium text-slate-700">{label}</p>
        {hint && <p className="mt-0.5 text-xs text-slate-400">{hint}</p>}
      </div>
      <div>{children}</div>
    </div>
  );
}

export default function SettingsPage() {
  const { user } = useAuth();
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [usage, setUsage] = useState<SystemUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<SectionKey>("profile");
  const [saved, setSaved] = useState<SectionKey | null>(null);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const displayName =
    (user?.user_metadata?.full_name as string | undefined) ||
    user?.email?.split("@")[0] ||
    "User";

  const [profile, setProfile] = useState({
    fullName: "",
    company: "",
    role: "",
    bio: "",
    timezone: "UTC",
    language: "en",
  });

  const [passwords, setPasswords] = useState({
    current: "",
    next: "",
    confirm: "",
  });
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const [prefs, setPrefs] = useState({
    theme: "light",
    density: "comfortable",
    autoStart: true,
    reportFormat: "pdf",
    defaultDepth: "standard",
  });

  const [notifications, setNotifications] = useState({
    analysisComplete: true,
    highRisk: true,
    weeklyDigest: false,
    productUpdates: false,
    marketing: false,
  });

  const [security, setSecurity] = useState({
    twoFactor: false,
    sessionAlerts: true,
  });

  const [apiKeyRevealed, setApiKeyRevealed] = useState(false);

  useEffect(() => {
    if (!user) return;
    let active = true;
    const meta = (user.user_metadata ?? {}) as Record<string, unknown>;

    const applyMetadata = () => {
      setProfile({
        fullName:
          (meta.full_name as string | undefined) ||
          user.email?.split("@")[0] ||
          "",
        company: (meta.company as string | undefined) ?? "",
        role: (meta.role as string | undefined) ?? "",
        bio: (meta.bio as string | undefined) ?? "",
        timezone: (meta.timezone as string | undefined) ?? "UTC",
        language: (meta.language as string | undefined) ?? "en",
      });
      const storedPrefs = meta.preferences as Record<string, unknown> | undefined;
      if (storedPrefs) {
        setPrefs((prev) => ({
          ...prev,
          theme: (storedPrefs.theme as string) ?? prev.theme,
          density: (storedPrefs.density as string) ?? prev.density,
          autoStart:
            storedPrefs.autoStart !== undefined
              ? Boolean(storedPrefs.autoStart)
              : prev.autoStart,
          reportFormat:
            (storedPrefs.reportFormat as string) ?? prev.reportFormat,
          defaultDepth:
            (storedPrefs.defaultDepth as string) ?? prev.defaultDepth,
        }));
      }
      const storedSecurity = meta.security as Record<string, unknown> | undefined;
      if (storedSecurity) {
        setSecurity((prev) => ({
          twoFactor:
            storedSecurity.twoFactor !== undefined
              ? Boolean(storedSecurity.twoFactor)
              : prev.twoFactor,
          sessionAlerts:
            storedSecurity.sessionAlerts !== undefined
              ? Boolean(storedSecurity.sessionAlerts)
              : prev.sessionAlerts,
        }));
      }
      const storedNotifications = meta.notifications as
        | Record<string, unknown>
        | undefined;
      if (storedNotifications) {
        setNotifications((prev) => ({
          ...prev,
          analysisComplete:
            storedNotifications.analysisComplete !== undefined
              ? Boolean(storedNotifications.analysisComplete)
              : prev.analysisComplete,
          highRisk:
            storedNotifications.highRisk !== undefined
              ? Boolean(storedNotifications.highRisk)
              : prev.highRisk,
          weeklyDigest:
            storedNotifications.weeklyDigest !== undefined
              ? Boolean(storedNotifications.weeklyDigest)
              : prev.weeklyDigest,
          productUpdates:
            storedNotifications.productUpdates !== undefined
              ? Boolean(storedNotifications.productUpdates)
              : prev.productUpdates,
          marketing:
            storedNotifications.marketing !== undefined
              ? Boolean(storedNotifications.marketing)
              : prev.marketing,
        }));
      }
    };

    applyMetadata();

    (async () => {
      try {
        const data = await getProfile();
        if (!active || !data) return;
        setProfile({
          fullName: data.full_name || profile.fullName || (meta.full_name as string) || user.email?.split("@")[0] || "",
          company: data.company ?? "",
          role: data.role ?? "",
          bio: data.bio ?? "",
          timezone: data.timezone ?? "UTC",
          language: data.language ?? "en",
        });
        setAvatarUrl(data.avatar_url);
        if (data.preferences) {
          const p = data.preferences as Record<string, unknown>;
          setPrefs((prev) => ({
            ...prev,
            theme: (p.theme as string) ?? prev.theme,
            density: (p.density as string) ?? prev.density,
            autoStart: p.autoStart !== undefined ? Boolean(p.autoStart) : prev.autoStart,
            reportFormat: (p.reportFormat as string) ?? prev.reportFormat,
            defaultDepth: (p.defaultDepth as string) ?? prev.defaultDepth,
          }));
        }
        if (data.notifications) {
          const n = data.notifications as Record<string, unknown>;
          setNotifications((prev) => ({
            ...prev,
            analysisComplete: n.analysisComplete !== undefined ? Boolean(n.analysisComplete) : prev.analysisComplete,
            highRisk: n.highRisk !== undefined ? Boolean(n.highRisk) : prev.highRisk,
            weeklyDigest: n.weeklyDigest !== undefined ? Boolean(n.weeklyDigest) : prev.weeklyDigest,
            productUpdates: n.productUpdates !== undefined ? Boolean(n.productUpdates) : prev.productUpdates,
            marketing: n.marketing !== undefined ? Boolean(n.marketing) : prev.marketing,
          }));
        }
        if (data.security) {
          const s = data.security as Record<string, unknown>;
          setSecurity((prev) => ({
            twoFactor: s.twoFactor !== undefined ? Boolean(s.twoFactor) : prev.twoFactor,
            sessionAlerts: s.sessionAlerts !== undefined ? Boolean(s.sessionAlerts) : prev.sessionAlerts,
          }));
        }
      } catch {
        /* fall back to metadata */
      }
    })();

    return () => {
      active = false;
    };
  }, [user]);

  useEffect(() => {
    Promise.all([getSystemStatus(), getSystemUsage()])
      .then(([statusData, usageData]) => {
        setStatus(statusData);
        setUsage(usageData);
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load system status")
      )
      .finally(() => setLoading(false));
  }, []);

  const flashSaved = (section: SectionKey) => {
    setSaved(section);
    setTimeout(() => setSaved((current) => (current === section ? null : current)), 2500);
  };

  const handleProfileSave = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setActionError(null);
    try {
      const { error } = await supabase.auth.updateUser({
        data: {
          full_name: profile.fullName,
          company: profile.company,
          role: profile.role,
          bio: profile.bio,
          timezone: profile.timezone,
          language: profile.language,
        },
      });
      if (error) throw error;

      await updateProfile({
        full_name: profile.fullName,
        email: user?.email ?? null,
        company: profile.company,
        role: profile.role,
        bio: profile.bio,
        timezone: profile.timezone,
        language: profile.language,
      });

      flashSaved("profile");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to save profile");
    } finally {
      setSaving(false);
    }
  };

  const handleAvatarChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !user?.id) return;
    setSaving(true);
    setActionError(null);
    try {
      const ext = file.name.split(".").pop() || "png";
      const path = `${user.id}/${Date.now()}.${ext}`;
      const { error: uploadError } = await supabase.storage
        .from("avatars")
        .upload(path, file, { upsert: true });
      if (uploadError) throw uploadError;
      const { data } = supabase.storage.from("avatars").getPublicUrl(path);
      const url = data.publicUrl;
      await updateProfile({ avatar_url: url });
      await supabase.auth.updateUser({ data: { avatar_url: url } });
      setAvatarUrl(url);
      flashSaved("profile");
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : "Failed to upload avatar"
      );
    } finally {
      setSaving(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handlePasswordSave = async (e: FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    if (!passwords.current) {
      setPasswordError("Enter your current password.");
      return;
    }
    if (passwords.next.length < 8) {
      setPasswordError("New password must be at least 8 characters.");
      return;
    }
    if (passwords.next !== passwords.confirm) {
      setPasswordError("New passwords do not match.");
      return;
    }
    setSaving(true);
    try {
      // Verify the current password before changing it.
      if (user?.email) {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email: user.email,
          password: passwords.current,
        });
        if (signInError) throw new Error("Current password is incorrect.");
      }
      const { error } = await supabase.auth.updateUser({ password: passwords.next });
      if (error) throw error;
      setPasswords({ current: "", next: "", confirm: "" });
      flashSaved("account");
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : "Failed to update password");
    } finally {
      setSaving(false);
    }
  };

  const usagePercent = status
    ? Math.min(100, (status.analysis_count / status.max_analyses) * 100)
    : 0;

  const initials = (displayName || "U")
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const copyToClipboard = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      flashSaved("security");
    } catch {
      /* noop */
    }
  };

  const renderContent = () => {
    switch (active) {
      case "profile":
        return (
          <SectionCard
            title="Profile information"
            description="Update your personal details and how you appear across the workspace."
            footer={
              <>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setProfile((p) => ({ ...p, fullName: displayName }))}
                >
                  Reset
                </Button>
                <Button type="submit" form="profile-form" size="sm" disabled={saving}>
                  {saving ? (
                    <>
                      <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      Saving changes...
                    </>
                  ) : saved === "profile" ? (
                    <>
                      <Check className="mr-2 h-4 w-4 text-emerald-500" />
                      <span className="text-emerald-600">Changes saved</span>
                    </>
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      Save changes
                    </>
                  )}
                </Button>
              </>
            }
          >
            <form id="profile-form" onSubmit={handleProfileSave} className="space-y-6">
              <div className="flex items-center gap-4">
                {avatarUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={avatarUrl}
                    alt="Avatar"
                    className="h-16 w-16 rounded-2xl object-cover shadow-md ring-2 ring-white"
                  />
                ) : (
                  <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 text-lg font-bold text-white shadow-md ring-2 ring-white">
                    {initials}
                  </span>
                )}
                <div>
                  <p className="text-sm font-semibold text-slate-900">{displayName}</p>
                  <p className="text-xs text-slate-500">{user?.email}</p>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="mt-2 text-xs font-medium text-blue-600 hover:text-blue-700"
                  >
                    Change avatar
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleAvatarChange}
                  />
                </div>
              </div>

              <div className="space-y-5">
                <FieldRow label="Full name" hint="Shown in reports and activity.">
                  <Input
                    value={profile.fullName}
                    onChange={(e) =>
                      setProfile((p) => ({ ...p, fullName: e.target.value }))
                    }
                    placeholder="Your full name"
                  />
                </FieldRow>
                <FieldRow label="Email">
                  <Input value={user?.email ?? ""} disabled />
                </FieldRow>
                <FieldRow label="Company / firm">
                  <Input
                    value={profile.company}
                    onChange={(e) =>
                      setProfile((p) => ({ ...p, company: e.target.value }))
                    }
                    placeholder="Ventrix Capital"
                  />
                </FieldRow>
                <FieldRow label="Role">
                  <Input
                    value={profile.role}
                    onChange={(e) =>
                      setProfile((p) => ({ ...p, role: e.target.value }))
                    }
                    placeholder="Investor / Analyst"
                  />
                </FieldRow>
                <FieldRow label="Bio">
                  <Textarea
                    value={profile.bio}
                    onChange={(e) =>
                      setProfile((p) => ({ ...p, bio: e.target.value }))
                    }
                    placeholder="A short description of your investment focus…"
                    rows={3}
                  />
                </FieldRow>
                <FieldRow label="Timezone">
                  <Select
                    value={profile.timezone}
                    onChange={(e) =>
                      setProfile((p) => ({ ...p, timezone: e.target.value }))
                    }
                  >
                    <option value="UTC">UTC</option>
                    <option value="America/New_York">America/New_York</option>
                    <option value="America/Los_Angeles">America/Los_Angeles</option>
                    <option value="Europe/London">Europe/London</option>
                    <option value="Asia/Kolkata">Asia/Kolkata</option>
                  </Select>
                </FieldRow>
                <FieldRow label="Language">
                  <Select
                    value={profile.language}
                    onChange={(e) =>
                      setProfile((p) => ({ ...p, language: e.target.value }))
                    }
                  >
                    <option value="en">English</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                  </Select>
                </FieldRow>
              </div>
            </form>
          </SectionCard>
        );

      case "account":
        return (
          <>
            <SectionCard
              title="Account details"
              description="Your account identity and sign-in information."
            >
              <div className="space-y-5">
                <FieldRow label="Email">
                  <Input value={user?.email ?? "—"} disabled />
                </FieldRow>
                <FieldRow label="Account created">
                  <Input
                    value={
                      user?.created_at
                        ? new Date(user.created_at).toLocaleString()
                        : "—"
                    }
                    disabled
                  />
                </FieldRow>
                <FieldRow label="Last sign in">
                  <Input
                    value={
                      user?.last_sign_in_at
                        ? new Date(user.last_sign_in_at).toLocaleString()
                        : "—"
                    }
                    disabled
                  />
                </FieldRow>
              </div>
            </SectionCard>

            <div className="mt-6">
              <SectionCard
                title="Change password"
                description="Use a strong password that you don't reuse elsewhere."
                footer={
                  <Button type="submit" form="password-form" size="sm" disabled={saving}>
                    {saving ? (
                      <>
                        <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                        Saving changes...
                      </>
                    ) : saved === "account" ? (
                      <>
                        <Check className="mr-2 h-4 w-4 text-emerald-500" />
                        <span className="text-emerald-600">Changes saved</span>
                      </>
                    ) : (
                      <>
                        <Lock className="mr-2 h-4 w-4" />
                        Update password
                      </>
                    )}
                  </Button>
                }
              >
                <form id="password-form" onSubmit={handlePasswordSave} className="space-y-5">
                  {passwordError && (
                    <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                      {passwordError}
                    </div>
                  )}
                  <FieldRow label="Current password">
                    <Input
                      type="password"
                      value={passwords.current}
                      onChange={(e) =>
                        setPasswords((p) => ({ ...p, current: e.target.value }))
                      }
                      placeholder="••••••••"
                    />
                  </FieldRow>
                  <FieldRow label="New password">
                    <Input
                      type="password"
                      value={passwords.next}
                      onChange={(e) =>
                        setPasswords((p) => ({ ...p, next: e.target.value }))
                      }
                      placeholder="At least 8 characters"
                    />
                  </FieldRow>
                  <FieldRow label="Confirm new password">
                    <Input
                      type="password"
                      value={passwords.confirm}
                      onChange={(e) =>
                        setPasswords((p) => ({ ...p, confirm: e.target.value }))
                      }
                      placeholder="Repeat new password"
                    />
                  </FieldRow>
                </form>
              </SectionCard>
            </div>
          </>
        );

      case "preferences":
        return (
          <SectionCard
            title="Workspace preferences"
            description="Customize how Ventrix behaves for you."
            footer={
              <Button
              size="sm"
              disabled={saving}
              onClick={async () => {
                setSaving(true);
                setActionError(null);
                try {
                  const { error } = await supabase.auth.updateUser({
                    data: { preferences: prefs },
                  });
                  if (error) throw error;
                  await updateProfile({ preferences: prefs });
                  flashSaved("preferences");
                } catch (err) {
                  setActionError(
                    err instanceof Error ? err.message : "Failed to save preferences"
                  );
                } finally {
                  setSaving(false);
                }
              }}
            >
                {saving ? (
                  <>
                    <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    Saving changes...
                  </>
                ) : saved === "preferences" ? (
                  <>
                    <Check className="mr-2 h-4 w-4 text-emerald-500" />
                    <span className="text-emerald-600">Changes saved</span>
                  </>
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    Save preferences
                  </>
                )}
              </Button>
            }
          >
            <div className="space-y-6">
              <FieldRow label="Theme" hint="Visual appearance.">
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { value: "light", label: "Light", icon: Palette },
                    { value: "dark", label: "Dark", icon: Monitor },
                    { value: "system", label: "System", icon: Settings2 },
                  ].map((option) => {
                    const Icon = option.icon;
                    const activeOption = prefs.theme === option.value;
                    return (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() =>
                          setPrefs((p) => ({ ...p, theme: option.value }))
                        }
                        className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-2.5 text-sm font-medium transition-all ${
                          activeOption
                            ? "border-blue-200 bg-blue-50 text-blue-700 shadow-sm"
                            : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
                        }`}
                      >
                        <Icon className="h-4 w-4" />
                        {option.label}
                      </button>
                    );
                  })}
                </div>
              </FieldRow>

              <FieldRow label="Display density">
                <Select
                  value={prefs.density}
                  onChange={(e) =>
                    setPrefs((p) => ({ ...p, density: e.target.value }))
                  }
                >
                  <option value="compact">Compact</option>
                  <option value="comfortable">Comfortable</option>
                  <option value="spacious">Spacious</option>
                </Select>
              </FieldRow>

              <FieldRow label="Default analysis depth">
                <Select
                  value={prefs.defaultDepth}
                  onChange={(e) =>
                    setPrefs((p) => ({ ...p, defaultDepth: e.target.value }))
                  }
                >
                  <option value="quick">Quick scan</option>
                  <option value="standard">Standard diligence</option>
                  <option value="deep">Deep diligence</option>
                </Select>
              </FieldRow>

              <FieldRow label="Report export format">
                <Select
                  value={prefs.reportFormat}
                  onChange={(e) =>
                    setPrefs((p) => ({ ...p, reportFormat: e.target.value }))
                  }
                >
                  <option value="pdf">PDF</option>
                  <option value="docx">DOCX</option>
                  <option value="html">HTML</option>
                </Select>
              </FieldRow>

              <FieldRow label="Auto-start workflow" hint="Run agents automatically after creating an analysis.">
                <Switch
                  checked={prefs.autoStart}
                  onChange={(v) => setPrefs((p) => ({ ...p, autoStart: v }))}
                  label="Auto-start workflow"
                />
              </FieldRow>
            </div>
          </SectionCard>
        );

      case "notifications":
        return (
          <SectionCard
            title="Notification preferences"
            description="Choose what you want to be notified about."
            footer={
              <Button
              size="sm"
              disabled={saving}
              onClick={async () => {
                setSaving(true);
                setActionError(null);
                try {
                  const { error } = await supabase.auth.updateUser({
                    data: { notifications },
                  });
                  if (error) throw error;
                  await updateProfile({ notifications });
                  flashSaved("notifications");
                } catch (err) {
                  setActionError(
                    err instanceof Error ? err.message : "Failed to save notifications"
                  );
                } finally {
                  setSaving(false);
                }
              }}
            >
                {saving ? (
                  <>
                    <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    Saving changes...
                  </>
                ) : saved === "notifications" ? (
                  <>
                    <Check className="mr-2 h-4 w-4 text-emerald-500" />
                    <span className="text-emerald-600">Changes saved</span>
                  </>
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    Save notifications
                  </>
                )}
              </Button>
            }
          >
            <div className="space-y-1">
              {[
                {
                  key: "analysisComplete" as const,
                  label: "Analysis completed",
                  hint: "When a diligence run finishes.",
                },
                {
                  key: "highRisk" as const,
                  label: "High-risk findings",
                  hint: "When a startup is flagged high or critical risk.",
                },
                {
                  key: "weeklyDigest" as const,
                  label: "Weekly digest",
                  hint: "Summary of workspace activity every Monday.",
                },
                {
                  key: "productUpdates" as const,
                  label: "Product updates",
                  hint: "New features and improvements.",
                },
                {
                  key: "marketing" as const,
                  label: "Marketing emails",
                  hint: "Tips, case studies, and offers.",
                },
              ].map((item) => (
                <div
                  key={item.key}
                  className="flex items-center justify-between rounded-xl border border-transparent px-2 py-3 transition-colors hover:bg-slate-50"
                >
                  <div>
                    <p className="text-sm font-medium text-slate-700">{item.label}</p>
                    <p className="text-xs text-slate-400">{item.hint}</p>
                  </div>
                  <Switch
                    checked={notifications[item.key]}
                    onChange={(v) =>
                      setNotifications((n) => ({ ...n, [item.key]: v }))
                    }
                    label={item.label}
                  />
                </div>
              ))}
            </div>
          </SectionCard>
        );

      case "security":
        return (
          <>
            <SectionCard
              title="Two-factor authentication"
              description="Add an extra layer of security to your account."
            >
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-slate-700">
                    Authenticator app
                  </p>
                  <p className="text-xs text-slate-400">
                    {security.twoFactor
                      ? "Enabled — your account is protected."
                      : "Not enabled. Recommended for all accounts."}
                  </p>
                </div>
                <Switch
                  checked={security.twoFactor}
                  onChange={async (v) => {
                    const next = { ...security, twoFactor: v };
                    setSecurity(next);
                    try {
                      await supabase.auth.updateUser({ data: { security: next } });
                      await updateProfile({ security: next });
                      flashSaved("security");
                    } catch {
                      /* noop */
                    }
                  }}
                  label="Two-factor authentication"
                />
              </div>
            </SectionCard>

            <div className="mt-6">
              <SectionCard
                title="Active sessions"
                description="Devices currently signed in to your account."
              >
                <div className="space-y-3">
                  {[
                    {
                      device: "Chrome on Windows",
                      location: "Bengaluru, IN",
                      current: true,
                      last: "Active now",
                    },
                    {
                      device: "Safari on iPhone",
                      location: "Bengaluru, IN",
                      current: false,
                      last: "2 days ago",
                    },
                  ].map((session) => (
                    <div
                      key={session.device}
                      className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3"
                    >
                      <div className="flex items-center gap-3">
                        <Monitor className="h-4 w-4 text-slate-400" />
                        <div>
                          <p className="text-sm font-medium text-slate-700">
                            {session.device}
                            {session.current && (
                              <Badge variant="success" className="ml-2">
                                Current
                              </Badge>
                            )}
                          </p>
                          <p className="text-xs text-slate-400">
                            {session.location} · {session.last}
                          </p>
                        </div>
                      </div>
                      {!session.current && (
                        <button
                          type="button"
                          className="text-xs font-medium text-rose-600 hover:text-rose-700"
                        >
                          Revoke
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </SectionCard>
            </div>

            {saved === "security" && (
              <p className="mt-3 text-xs font-medium text-emerald-600">
                Security settings updated.
              </p>
            )}
          </>
        );

      case "integrations":
        return (
          <SectionCard
            title="Connected providers"
            description="AI and data providers powering your analyses."
          >
            {loading && (
              <p className="text-sm text-slate-400">Loading provider status…</p>
            )}
            {error && <p className="text-sm text-rose-600">{error}</p>}
            {status && (
              <div className="space-y-3">
                <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3">
                  <div>
                    <p className="text-sm font-medium text-slate-700">
                      Active provider
                    </p>
                    <p className="text-xs text-slate-400">
                      {status.active_provider}
                    </p>
                  </div>
                  <Badge variant="success">Active</Badge>
                </div>
                {status.providers.map((provider) => (
                  <div
                    key={provider.name}
                    className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <Plug className="h-4 w-4 text-slate-400" />
                      <div>
                        <p className="text-sm font-medium text-slate-700">
                          {provider.name}
                        </p>
                        <p className="text-xs text-slate-400">
                          {provider.active ? "Currently in use" : "Available"}
                        </p>
                      </div>
                    </div>
                    <Badge variant={provider.configured ? "success" : "neutral"}>
                      {provider.configured ? "Configured" : "Not configured"}
                    </Badge>
                  </div>
                ))}
                <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-3">
                  <p className="text-xs font-medium text-slate-500">
                    Fallback history
                  </p>
                  <p className="mt-1 text-sm text-slate-700">
                    {status.fallback_history.length
                      ? status.fallback_history.join(", ")
                      : "No fallbacks triggered."}
                  </p>
                </div>
              </div>
            )}
          </SectionCard>
        );

      case "usage":
        return (
          <>
            <SectionCard
              title="Usage & billing"
              description="Track your analysis consumption and plan limits."
            >
              {loading && (
                <p className="text-sm text-slate-400">Loading usage…</p>
              )}
              {status && (
                <div className="space-y-5">
                  <div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-slate-700">
                        Analyses used
                      </span>
                      <span className="text-slate-500">
                        {usage
                          ? `${usage.completed_analyses} of ${usage.max_analyses}`
                          : `${status.analysis_count} of ${status.max_analyses}`}
                      </span>
                    </div>
                    <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all"
                        style={{ width: `${usagePercent}%` }}
                      />
                    </div>
                    <p className="mt-2 text-xs text-slate-400">
                      {usage
                        ? `${usage.remaining_analyses} analyses remaining${
                            usage.limit_reached ? " — limit reached" : ""
                          }`
                        : `${status.max_analyses - status.analysis_count} remaining`}
                    </p>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                        Plan
                      </p>
                      <p className="mt-1 text-sm font-semibold text-slate-900">
                        Pro workspace
                      </p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                        Version
                      </p>
                      <p className="mt-1 text-sm font-semibold text-slate-900">
                        {status.version}
                      </p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                        API status
                      </p>
                      <p className="mt-1 text-sm font-semibold text-slate-900">
                        {status.api_status}
                      </p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                        Database
                      </p>
                      <p className="mt-1 text-sm font-semibold text-slate-900">
                        {status.database}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </SectionCard>

            <div className="mt-6">
              <SectionCard
                title="Billing"
                description="Manage your subscription and invoices."
              >
                <div className="flex flex-wrap items-center gap-3">
                  <Button variant="secondary" size="sm">
                    <CreditCard className="mr-2 h-4 w-4" />
                    Manage subscription
                  </Button>
                  <Button variant="ghost" size="sm">
                    Download invoices
                  </Button>
                </div>
                <p className="mt-3 text-xs text-slate-400">
                  Billing is handled by your workspace administrator. Contact
                  support to change plans.
                </p>
              </SectionCard>
            </div>
          </>
        );

      case "danger":
        return (
          <SectionCard
            title="Danger zone"
            description="Irreversible and destructive actions."
          >
            <div className="space-y-4">
              <div className="flex flex-col gap-3 rounded-xl border border-rose-200 bg-rose-50/40 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold text-rose-700">
                    Export account data
                  </p>
                  <p className="text-xs text-rose-600/80">
                    Download a copy of all your analyses and reports.
                  </p>
                </div>
                <Button variant="secondary" size="sm">
                  Export data
                </Button>
              </div>

              <div className="flex flex-col gap-3 rounded-xl border border-rose-200 bg-rose-50/40 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold text-rose-700">
                    Delete account
                  </p>
                  <p className="text-xs text-rose-600/80">
                    Permanently delete your account and all associated data. This
                    cannot be undone.
                  </p>
                </div>
                <Button
                  variant="primary"
                  size="sm"
                  className="bg-rose-600 hover:bg-rose-700 shadow-[0_10px_24px_-12px_rgba(220,38,38,0.9)]"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete account
                </Button>
              </div>
            </div>
          </SectionCard>
        );

      default:
        return null;
    }
  };

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Settings"
        title="Account settings"
        description="Manage your profile, preferences, security, and workspace configuration."
      />

      {actionError && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {actionError}
        </div>
      )}

      <div className="lg:hidden">
        <Select
          value={active}
          onChange={(e) => setActive(e.target.value as SectionKey)}
        >
          {sections.map((s) => (
            <option key={s.key} value={s.key}>
              {s.label}
            </option>
          ))}
        </Select>
      </div>

      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        {/* Sidebar nav */}
        <aside className="hidden lg:block lg:sticky lg:top-24 lg:self-start">
          <Card className="p-2">
            <nav className="space-y-1" aria-label="Settings sections">
              {sections.map((section) => {
                const Icon = section.icon;
                const isActive = active === section.key;
                return (
                  <button
                    key={section.key}
                    type="button"
                    onClick={() => setActive(section.key)}
                    className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
                      isActive
                        ? "bg-gradient-to-r from-blue-50 to-indigo-50/60 text-blue-700 shadow-[inset_0_0_0_1px_rgba(37,99,235,0.12)]"
                        : "text-slate-500 hover:bg-slate-100/80 hover:text-slate-900"
                    }`}
                  >
                    <Icon
                      className={`h-4 w-4 shrink-0 ${
                        isActive ? "text-blue-600" : "text-slate-400"
                      }`}
                    />
                    <span className="flex-1 text-left">{section.label}</span>
                    {isActive && (
                      <ChevronRight className="h-4 w-4 text-blue-400" />
                    )}
                  </button>
                );
              })}
            </nav>
          </Card>


        </aside>

        {/* Content */}
        <div className="min-w-0">{renderContent()}</div>
      </div>

    </div>
  );
}