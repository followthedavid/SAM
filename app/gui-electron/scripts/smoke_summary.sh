#!/usr/bin/env bash
set -euo pipefail
LOGDIR="$HOME/.warp_open/sessions"
latest() { ls -t "$LOGDIR"/session-*.jsonl 2>/dev/null | head -1; }
LOG="$(latest || true)"
[ -n "${LOG:-}" ] || { echo "No session-*.jsonl logs found in $LOGDIR"; exit 1; }

echo "== Smoke summary: $(basename "$LOG") =="
jq -r '
  def short: .[0:96] + (if (length>96) then "…" else "" end);
  reduce (inputs) as $r (
    {seq:0,start:null,exit:null,inputs:0,outputs:0};
    . as $acc
    | if $r.type=="smoke:start" then .start=$r.t
      elif $r.type=="pty:exit"  then .exit=$r.t
      elif $r.type=="pty:input" then .inputs += 1
      elif $r.type=="pty:data"  then .outputs += 1
      else . end
  ) as $tot
  | "start=\($tot.start) exit=\($tot.exit) inputs=\($tot.inputs) outputs=\($tot.outputs)"
' < <(jq -c '.' "$LOG")

echo "-- Key events --"
jq -r '
  def short: .[0:96] + (if (length>96) then "…" else "" end);
  . as $r
  | if   .type=="pty:start" then "[pty:start] cols=\(.cols) rows=\(.rows) cwd=\(.cwd)"
    elif .type=="pty:input" then "[pty:input] " + (.data|tostring|gsub("\r";"\\r")|gsub("\n";"\\n")|short)
    elif .type=="pty:data"  then "[pty:data]  " + (.data|tostring|gsub("\r";"\\r")|gsub("\n";"\\n")|short)
    elif .type=="pty:exit"  then "[pty:exit] code=\(.code) signal=\(.signal)"
    elif .type=="smoke:timeout" then "[smoke:timeout]"
    elif .type=="smoke:done"    then "[smoke:done]"
    else empty end
' "$LOG" | sed -n '1,60p'
