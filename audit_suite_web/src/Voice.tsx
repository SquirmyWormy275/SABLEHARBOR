import { useEffect, useRef, useState } from "react";
import { request, requestAudio } from "./api";
export function VoiceInput({
  engagement,
  enabled,
  onConfirm,
}: {
  engagement: string;
  enabled: boolean;
  onConfirm: (text: string) => void;
}) {
  const [recording, setRecording] = useState(false),
    [working, setWorking] = useState(false),
    [text, setText] = useState(""),
    [error, setError] = useState("");
  const recorder = useRef<MediaRecorder | null>(null),
    stream = useRef<MediaStream | null>(null),
    cancelled = useRef(false),
    mounted = useRef(true),
    timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      cancelled.current = true;
      recorder.current?.state === "recording" && recorder.current.stop();
      stream.current?.getTracks().forEach((t) => t.stop());
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);
  const supported =
    typeof MediaRecorder !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia;
  async function start() {
    setWorking(true);
    setError("");
    setText("");
    cancelled.current = false;
    try {
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!mounted.current) {
        media.getTracks().forEach((t) => t.stop());
        return;
      }
      stream.current = media;
      const type = [
        "audio/webm;codecs=opus",
        "audio/ogg;codecs=opus",
        "audio/mp4",
      ].find((t) => MediaRecorder.isTypeSupported(t));
      const r = new MediaRecorder(media, type ? { mimeType: type } : undefined);
      recorder.current = r;
      const chunks: BlobPart[] = [];
      r.ondataavailable = (e) => {
        if (e.data.size) chunks.push(e.data);
      };
      r.onstop = async () => {
        media.getTracks().forEach((t) => t.stop());
        if (timer.current) clearTimeout(timer.current);
        if (!mounted.current) return;
        setRecording(false);
        if (cancelled.current) return;
        setWorking(true);
        try {
          const blob = new Blob(chunks, { type: r.mimeType });
          if (blob.size > 12000000)
            throw Error(
              "Recording exceeds the local speech limit. Try a shorter message.",
            );
          const form = new FormData();
          form.set("file", blob, "recording.webm");
          const result = await request<{ text: string }>(
            `/api/engagements/${encodeURIComponent(engagement)}/voice/transcribe`,
            "POST",
            form,
          );
          if (!result.text.trim())
            throw Error(
              "No speech was recognized. Check the microphone and try again.",
            );
          if (mounted.current) setText(result.text);
        } catch (e) {
          if (mounted.current) setError((e as Error).message);
        } finally {
          if (mounted.current) setWorking(false);
        }
      };
      r.start(1000);
      setRecording(true);
      setWorking(false);
      timer.current = setTimeout(
        () => r.state === "recording" && r.stop(),
        110000,
      );
    } catch (e) {
      stream.current?.getTracks().forEach((t) => t.stop());
      setError((e as Error).message);
      setWorking(false);
    }
  }
  return (
    <section className="voice-input" aria-label="Local voice input">
      <div className="actions">
        <button
          type="button"
          disabled={!enabled || !supported || working}
          onClick={() => (recording ? recorder.current?.stop() : void start())}
        >
          {recording ? "Stop and transcribe" : "Record a voice draft"}
        </button>
        {recording && (
          <button
            type="button"
            onClick={() => {
              cancelled.current = true;
              recorder.current?.stop();
            }}
          >
            Discard recording
          </button>
        )}
        <span role="status">
          {recording
            ? "Recording · stops after 110 seconds"
            : working
              ? "Transcribing locally…"
              : !enabled
                ? "Local speech runtime unavailable"
                : !supported
                  ? "Microphone capture is unavailable in this browser"
                  : "English transcription · stays on this local service"}
        </span>
      </div>
      {error && <p role="alert">{error}</p>}
      {text && (
        <div className="transcript">
          <label>
            Review and correct the transcript
            <textarea
              aria-label="Review and correct the transcript"
              rows={3}
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </label>
          <button
            type="button"
            onClick={() => {
              onConfirm(text);
              setText("");
            }}
          >
            Use transcript in message draft
          </button>
          <small>
            Nothing is sent to the company until you send the message.
          </small>
        </div>
      )}
    </section>
  );
}
export function SpeakButton({
  engagement,
  message,
  enabled,
}: {
  engagement: string;
  message: string;
  enabled: boolean;
}) {
  const [busy, setBusy] = useState(false),
    [url, setURL] = useState(""),
    [error, setError] = useState("");
  useEffect(
    () => () => {
      if (url) URL.revokeObjectURL(url);
    },
    [url],
  );
  return (
    <div className="speech-output">
      <button
        type="button"
        disabled={!enabled || busy}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            const blob = await requestAudio(
              `/api/engagements/${encodeURIComponent(engagement)}/voice/synthesize`,
              { message_id: message },
            );
            setURL(URL.createObjectURL(blob));
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Preparing local audio…" : "Read aloud"}
      </button>
      {url && (
        <audio
          controls
          src={url}
          aria-label="Synthetic reading of company message"
        />
      )}
      {url && <small>Synthetic voice · original message retained above</small>}
      {error && <span role="alert">{error}</span>}
    </div>
  );
}
