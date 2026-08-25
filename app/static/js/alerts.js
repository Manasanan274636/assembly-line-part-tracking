/**
 * Assembly Line Alert System
 * Handles: sound alerts, toast notifications, visual effects
 */

// ─── Web Audio Context (created lazily on first user interaction) ─────────────
let _audioCtx = null;
function getAudioCtx() {
  if (!_audioCtx) {
    try { _audioCtx = new (window.AudioContext || window.webkitAudioContext)(); }
    catch(e) { return null; }
  }
  if (_audioCtx.state === 'suspended') _audioCtx.resume();
  return _audioCtx;
}

// Enable audio after first user interaction
document.addEventListener('click', getAudioCtx, { once: true });
document.addEventListener('keydown', getAudioCtx, { once: true });

// ─── Sound Generators ─────────────────────────────────────────────────────────
function playTone(frequency, duration, type, gain, delay) {
  type = type || 'sine'; gain = gain || 0.4; delay = delay || 0;
  const ctx = getAudioCtx();
  if (!ctx) return;
  const osc = ctx.createOscillator();
  const gainNode = ctx.createGain();
  osc.connect(gainNode);
  gainNode.connect(ctx.destination);
  osc.type = type;
  osc.frequency.setValueAtTime(frequency, ctx.currentTime + delay);
  gainNode.gain.setValueAtTime(0, ctx.currentTime + delay);
  gainNode.gain.linearRampToValueAtTime(gain, ctx.currentTime + delay + 0.02);
  gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + delay + duration);
  osc.start(ctx.currentTime + delay);
  osc.stop(ctx.currentTime + delay + duration);
}

window.AlertSound = {
  success: function() {
    playTone(523.25, 0.15, 'sine', 0.35, 0.00);
    playTone(659.25, 0.15, 'sine', 0.35, 0.12);
    playTone(783.99, 0.25, 'sine', 0.35, 0.24);
  },
  lowStock: function() {
    playTone(440, 0.18, 'triangle', 0.4, 0.00);
    playTone(370, 0.18, 'triangle', 0.4, 0.22);
    playTone(440, 0.18, 'triangle', 0.4, 0.44);
  },
  critical: function() {
    playTone(880, 0.12, 'square', 0.25, 0.00);
    playTone(660, 0.12, 'square', 0.25, 0.14);
    playTone(880, 0.12, 'square', 0.25, 0.28);
    playTone(550, 0.20, 'square', 0.25, 0.42);
  },
  info: function() {
    playTone(698.46, 0.2, 'sine', 0.3, 0.00);
  }
};

// ─── Toast Notification System ────────────────────────────────────────────────
(function initToastContainer() {
  if (document.getElementById('agl-toast-container')) return;
  const container = document.createElement('div');
  container.id = 'agl-toast-container';
  container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:10px;pointer-events:none;';
  document.body.appendChild(container);

  const style = document.createElement('style');
  style.textContent = `
    .agl-toast {
      display:flex;align-items:flex-start;gap:12px;
      background:#fff;border-radius:12px;
      box-shadow:0 8px 32px rgba(15,23,42,0.15),0 2px 8px rgba(15,23,42,0.08);
      padding:14px 16px;min-width:300px;max-width:380px;
      border-left:4px solid #3b82f6;pointer-events:all;
      animation:toastIn 0.35s cubic-bezier(0.34,1.56,0.64,1) forwards;
      position:relative;overflow:hidden;
    }
    .agl-toast.toast-success{border-left-color:#10b981;}
    .agl-toast.toast-warning{border-left-color:#f59e0b;}
    .agl-toast.toast-danger {border-left-color:#ef4444;}
    .agl-toast.toast-info   {border-left-color:#3b82f6;}
    .agl-toast.toast-out{animation:toastOut 0.3s ease forwards;}
    .agl-toast-icon{width:36px;height:36px;border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
    .toast-success .agl-toast-icon{background:#ecfdf5;color:#10b981;}
    .toast-warning .agl-toast-icon{background:#fffbeb;color:#f59e0b;}
    .toast-danger  .agl-toast-icon{background:#fef2f2;color:#ef4444;}
    .toast-info    .agl-toast-icon{background:#eff6ff;color:#3b82f6;}
    .agl-toast-body{flex:1;min-width:0;}
    .agl-toast-title{font-weight:600;font-size:13px;color:#0f172a;margin-bottom:2px;}
    .agl-toast-msg{font-size:12px;color:#64748b;line-height:1.4;}
    .agl-toast-progress{position:absolute;bottom:0;left:0;height:3px;background:currentColor;opacity:0.25;transition:width linear;}
    .agl-toast-close{background:none;border:none;cursor:pointer;color:#94a3b8;font-size:18px;padding:0;line-height:1;flex-shrink:0;margin-top:0px;}
    .agl-toast-close:hover{color:#475569;}
    @keyframes toastIn{from{opacity:0;transform:translateX(60px) scale(0.9);}to{opacity:1;transform:translateX(0) scale(1);}}
    @keyframes toastOut{from{opacity:1;transform:translateX(0) scale(1);max-height:120px;}to{opacity:0;transform:translateX(60px) scale(0.9);max-height:0;margin-bottom:-10px;padding:0;}}
    @keyframes criticalPulse{0%,100%{background-color:transparent;}50%{background-color:rgba(239,68,68,0.07);}}
    tr.critical-row{animation:criticalPulse 2s ease-in-out infinite;}
    tr.critical-row td:first-child{border-left:3px solid #ef4444 !important;}
    tr.low-row td:first-child{border-left:3px solid #f59e0b !important;}
    @keyframes scrapPulse{0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,0.4);}50%{box-shadow:0 0 0 6px rgba(239,68,68,0);}}
    .scrap-alert-badge{animation:scrapPulse 1.5s ease-in-out infinite;}
    .kpi-hover{transition:transform 0.25s ease,box-shadow 0.25s ease;}
    .kpi-hover:hover{transform:translateY(-4px);box-shadow:0 12px 32px rgba(15,23,42,0.12) !important;}
    .bom-row-enter{animation:bomIn 0.3s ease forwards;}
    @keyframes bomIn{from{opacity:0;transform:translateY(-6px);}to{opacity:1;transform:translateY(0);}}
  `;
  document.head.appendChild(style);
})();

var ICONS = {
  success:'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>',
  warning:'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
  danger: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
  info:   '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
};

window.showToast = function(type, title, msg, dur) {
  dur = dur || 4500;
  var container = document.getElementById('agl-toast-container');
  if (!container) return;
  var toast = document.createElement('div');
  toast.className = 'agl-toast toast-' + type;
  toast.innerHTML = '<div class="agl-toast-icon">' + (ICONS[type]||ICONS.info) + '</div>'
    + '<div class="agl-toast-body"><div class="agl-toast-title">' + title + '</div>'
    + (msg ? '<div class="agl-toast-msg">' + msg + '</div>' : '') + '</div>'
    + '<button class="agl-toast-close" onclick="this.closest(\'.agl-toast\').remove()">&#215;</button>'
    + '<div class="agl-toast-progress" style="width:100%;"></div>';
  container.appendChild(toast);
  var bar = toast.querySelector('.agl-toast-progress');
  requestAnimationFrame(function() {
    bar.style.transition = 'width ' + dur + 'ms linear';
    bar.style.width = '0%';
  });
  var timer = setTimeout(function() {
    toast.classList.add('toast-out');
    setTimeout(function(){ if(toast.parentElement) toast.remove(); }, 300);
  }, dur);
  toast.addEventListener('mouseenter', function(){ clearTimeout(timer); });
};

// ─── Auto-run on DOMContentLoaded ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  // Add pulse to critical rows in any table
  document.querySelectorAll('tr[data-status="Critical"], tr[data-status="Below Safety"]').forEach(function(row) {
    row.classList.add('critical-row');
  });
  document.querySelectorAll('tr[data-status="Low"], tr[data-status="Low Stock"]').forEach(function(row) {
    row.classList.add('low-row');
  });

  // Add hover lift to all cards
  document.querySelectorAll('.card.border-0').forEach(function(card) {
    card.classList.add('kpi-hover');
  });

  // Scrap badge pulse
  document.querySelectorAll('td input[class*="bg-danger"]').forEach(function(input) {
    var val = parseInt(input.value);
    if (!isNaN(val) && val > 0) input.classList.add('scrap-alert-badge');
  });

  // Flash messages from Flask → Toast (look for hidden data divs)
  document.querySelectorAll('[data-flash-type]').forEach(function(el) {
    var type = el.dataset.flashType;
    var msg  = el.dataset.flashMsg || el.textContent.trim();
    var title = type === 'success' ? 'Saved Successfully'
              : type === 'danger'  ? 'Alert — Action Required'
              : type === 'warning' ? 'Warning'
              : 'Notice';
    showToast(type, title, msg, type === 'danger' ? 6000 : 4500);
    // Play sound based on alert type
    if (type === 'danger')  { setTimeout(function(){ AlertSound.critical(); }, 300); }
    else if (type === 'warning') { setTimeout(function(){ AlertSound.lowStock(); }, 300); }
    else if (type === 'success') { setTimeout(function(){ AlertSound.success(); }, 300); }
    el.style.display = 'none';
  });
});
