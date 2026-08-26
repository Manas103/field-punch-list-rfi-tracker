import { OpenPunchItemForm } from "./components/OpenPunchItemForm";
import { TurnoverPanel } from "./components/TurnoverPanel";

export default function App() {
  return (
    <main>
      <h1>Field Punch List and RFI Tracker</h1>
      <OpenPunchItemForm />
      <TurnoverPanel />
    </main>
  );
}
