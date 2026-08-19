import React from 'react';
import { useParams } from 'react-router-dom';
import { ShieldAlert, CheckCircle2, AlertTriangle, Activity, HeartHandshake, PhoneCall } from 'lucide-react';
import { useWelfareMessages, useWelfareCheckByDevice, useRespondWelfareCheck } from '../hooks/useWelfareCheck';
import { WelfareCheckResponse } from '../lib/types';

export const VehicleCheckInPage: React.FC = () => {
  const { deviceCode } = useParams<{ deviceCode: string }>();
  const { data: messages, isLoading: isLoadingMessages } = useWelfareMessages();
  const { data: check, isLoading: isLoadingCheck, isError } = useWelfareCheckByDevice(deviceCode);
  const respondMutation = useRespondWelfareCheck();

  const handleRespond = (response: WelfareCheckResponse) => {
    if (!check) return;
    respondMutation.mutate({ checkId: check.id, response });
  };

  const promptText = check?.prompt || messages?.prompt || "We detected a possible accident. Are you able to respond?";
  const safetyText = check?.safety_guidance || messages?.safety_guidance || "Stay as still as possible. Do not attempt to move unless there is immediate danger (fire, traffic). Help is on the way.";
  const escalationText = check?.escalation_notice || messages?.escalation_notice || "No response received. Emergency responders have been notified with elevated priority.";

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between p-6 sm:p-10 font-sans select-none overflow-hidden relative">
      {/* Background Ambient Glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none animate-pulse" />

      {/* Header Bar */}
      <header className="flex items-center justify-between border-b border-slate-800/80 pb-4 relative z-10">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Activity className="w-6 h-6 animate-spin-slow" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100">Vehicle Emergency Assistant</h1>
            <p className="text-xs font-mono text-slate-400">Unit ID: <span className="text-cyan-400 font-bold">{deviceCode || 'UNKNOWN'}</span></p>
          </div>
        </div>
        <div className="flex items-center gap-2 bg-slate-900/80 px-3.5 py-1.5 rounded-full border border-slate-800 text-xs font-mono">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
          <span className="text-slate-300">SYSTEM MONITORED</span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col justify-center items-center max-w-3xl mx-auto w-full py-8 relative z-10">
        {isLoadingCheck || isLoadingMessages ? (
          <div className="glass-card rounded-2xl p-8 text-center space-y-4 border border-slate-800">
            <Activity className="w-10 h-10 text-cyan-400 animate-spin mx-auto" />
            <p className="text-slate-400 text-sm font-mono">Connecting to Onboard Telemetry...</p>
          </div>
        ) : isError || !check ? (
          <div className="glass-card rounded-3xl p-10 text-center space-y-4 border border-slate-800/80 max-w-lg shadow-2xl">
            <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto">
              <ShieldAlert className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold text-slate-100">All Systems Normal</h2>
            <p className="text-sm text-slate-400 leading-relaxed">
              No active accident welfare checks for vehicle <span className="font-mono text-cyan-400 font-semibold">{deviceCode}</span>.
              Continuous sensor monitoring is active.
            </p>
          </div>
        ) : check.status === 'awaiting_response' ? (
          /* State 1: Awaiting Occupant Response */
          <div className="w-full space-y-8 animate-fade-in">
            <div className="glass-card rounded-3xl p-8 sm:p-10 border border-amber-500/30 bg-amber-500/5 shadow-2xl text-center space-y-4">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-mono font-bold uppercase tracking-wider animate-pulse">
                <AlertTriangle className="w-4 h-4" /> Crash Detection Alert
              </div>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-100 leading-snug">
                {promptText}
              </h2>
              <p className="text-sm text-slate-400">
                Please tap an option below to notify dispatch operators immediately.
              </p>
            </div>

            {/* Large Touch Action Buttons */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 w-full">
              <button
                onClick={() => handleRespond('ok')}
                disabled={respondMutation.isPending}
                className="group relative flex flex-col items-center justify-center gap-3 p-8 rounded-3xl bg-gradient-to-b from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 active:scale-[0.98] transition-all duration-150 text-white shadow-xl shadow-emerald-950/50 border border-emerald-400/30"
              >
                <CheckCircle2 className="w-12 h-12 text-emerald-200 group-hover:scale-110 transition-transform" />
                <span className="text-2xl font-black tracking-wider uppercase">I'M OK</span>
                <span className="text-xs text-emerald-100/80 font-medium">Minor crash / No injuries needed</span>
              </button>

              <button
                onClick={() => handleRespond('help')}
                disabled={respondMutation.isPending}
                className="group relative flex flex-col items-center justify-center gap-3 p-8 rounded-3xl bg-gradient-to-b from-rose-600 to-rose-700 hover:from-rose-500 hover:to-rose-600 active:scale-[0.98] transition-all duration-150 text-white shadow-xl shadow-rose-950/50 border border-rose-400/30"
              >
                <PhoneCall className="w-12 h-12 text-rose-200 group-hover:scale-110 transition-transform animate-bounce" />
                <span className="text-2xl font-black tracking-wider uppercase">I NEED HELP</span>
                <span className="text-xs text-rose-100/80 font-medium">Request immediate emergency response</span>
              </button>
            </div>
          </div>
        ) : (
          /* State 2 & 3: Responded or Escalated */
          <div className="w-full space-y-6 animate-fade-in">
            {check.status === 'no_response_escalated' ? (
              <div className="glass-card rounded-3xl p-8 border border-rose-500/40 bg-rose-950/40 text-center space-y-3 shadow-2xl">
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40 text-xs font-mono font-bold uppercase tracking-wider">
                  <ShieldAlert className="w-4 h-4 text-rose-400" /> Automated Escalation Triggered
                </div>
                <h2 className="text-xl font-bold text-rose-200 leading-snug">
                  {escalationText}
                </h2>
              </div>
            ) : check.status === 'responded_help' ? (
              <div className="glass-card rounded-3xl p-8 border border-rose-500/40 bg-rose-950/40 text-center space-y-3 shadow-2xl">
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40 text-xs font-mono font-bold uppercase tracking-wider">
                  <PhoneCall className="w-4 h-4 text-rose-400" /> Emergency Help Requested
                </div>
                <h2 className="text-xl font-bold text-rose-200">
                  Occupant Requested Assistance
                </h2>
              </div>
            ) : (
              <div className="glass-card rounded-3xl p-8 border border-emerald-500/40 bg-emerald-950/40 text-center space-y-3 shadow-2xl">
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-mono font-bold uppercase tracking-wider">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Response Logged: OK
                </div>
                <h2 className="text-xl font-bold text-emerald-200">
                  Occupant Confirmed Safe
                </h2>
              </div>
            )}

            {/* Static Universal Safety Guidance Card */}
            <div className="glass-card rounded-3xl p-8 border border-cyan-500/30 bg-cyan-950/30 shadow-2xl text-center space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 flex items-center justify-center mx-auto">
                <HeartHandshake className="w-6 h-6" />
              </div>
              <h3 className="text-xs font-mono font-semibold uppercase tracking-widest text-cyan-400">
                Safety & Guidance Protocol
              </h3>
              <p className="text-base text-slate-200 leading-relaxed font-medium">
                "{safetyText}"
              </p>
            </div>
          </div>
        )}
      </main>

      {/* Footer Info */}
      <footer className="border-t border-slate-800/80 pt-4 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 font-mono gap-2 relative z-10">
        <div>SMART ACCIDENT RESPONSE SYSTEM &bull; IN-VEHICLE TELEMETRY NODE</div>
        <div>STATION ID: {deviceCode}</div>
      </footer>
    </div>
  );
};
