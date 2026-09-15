import {
  LayoutDashboard,
} from "lucide-react";


function RunPanel() {
  return (
    <section className="panel run-panel">
      <div className="panel-heading compact">
        <div>
          <div className="section-eyebrow">
            Runtime
          </div>

          <h3>Latest run</h3>
        </div>
      </div>

      <div className="empty-run">
        <LayoutDashboard
          size={26}
          strokeWidth={1.5}
        />

        <div>
          <strong>
            No runs available
          </strong>

          <span>
            Calibration and prediction runs
            will appear here.
          </span>
        </div>
      </div>
    </section>
  );
}


export default RunPanel;
