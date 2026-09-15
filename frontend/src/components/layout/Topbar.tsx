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
    </header>
  );
}


export default Topbar;
