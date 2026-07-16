const GLB_SRC = "/assets/media/container.glb";
const LIDAR_MP4 = "/assets/media/lidar_scan.mp4";

// 3D container center stage; during a LiDAR scan the mockup video
// crossfades in over the model, then hands back on ended/error.
export default function CenterStage({ scanning, visionScanning, onScanEnd }) {
  return (
    <div className="center-stage">
      <div className={`fade-layer ${scanning ? "opacity-0" : "opacity-100"}`}>
        <model-viewer
          src={GLB_SRC}
          alt="โมเดลตู้คอนเทนเนอร์"
          camera-controls=""
          auto-rotate=""
          rotation-per-second="12deg"
          interaction-prompt="none"
          shadow-intensity="0.6"
          environment-image="neutral"
          exposure="1.6"
        />
        {visionScanning && (
          <div className="viz-loader">
            <div className="viz-ring" />
            <span className="viz-label">Vision scanning…</span>
            <div className="viz-bar" />
          </div>
        )}
      </div>
      <div className={`fade-layer ${scanning ? "opacity-100" : "pointer-events-none opacity-0"}`}>
        {scanning && (
          <video
            src={LIDAR_MP4}
            className="h-full w-full rounded-xl object-contain"
            autoPlay
            muted
            playsInline
            onEnded={onScanEnd}
            onError={onScanEnd}
          />
        )}
        <div className="scanlines rounded-xl" />
      </div>
    </div>
  );
}
