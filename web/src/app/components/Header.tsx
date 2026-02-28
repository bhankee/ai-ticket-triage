const Header = () => {
  return (
    <>
      <h1 className="text-3xl font-bold">AI Ticket Triage</h1>
      <p className="text-sm text-gray-500 mt-2">
        Read-only internal tool dashboard (FastAPI + SQLite). Outputs are
        deterministic and require human validation for flagged items.
      </p>
    </>
  );
};

export default Header;
