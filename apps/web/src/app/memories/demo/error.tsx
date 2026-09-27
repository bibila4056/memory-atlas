"use client";

export default function DemoError({ reset }: { reset: () => void }) {
  return <main className="error-page"><p className="wordmark">Memory Atlas</p><h1>This spread couldn’t be opened.</h1>
    <p>Please try again in a moment.</p><button onClick={reset}>Try again</button></main>;
}
