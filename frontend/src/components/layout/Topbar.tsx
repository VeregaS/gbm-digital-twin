import {
  CircleDot,
  Settings2,
} from "lucide-react";


type TopbarProps = {
  pageTitle: string;
};


function Topbar({
  pageTitle,
}: TopbarProps) {
  return (
    <header className="topbar">
      <div>
        <div className="topbar-context">
          Digital Twin Workbench
        </div>

        <h1>{pageTitle}</h1>
      </div>

      <div className="topbar-actions">
        <div className="model-pill">
          <CircleDot size={15} />
          <span>
            V2 · Latent PIRT
          </span>
        </div>

        <button
          type="button"
          className="icon-button"
          aria-label="Settings"
        >
          <Settings2 size={18} />
        </button>
      </div>
    </header>
  );
}


export default Topbar;
