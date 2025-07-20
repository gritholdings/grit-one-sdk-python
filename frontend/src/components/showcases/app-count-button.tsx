import { useState } from 'react'
import { Button } from '../ui/button'


export function AppCountButton() {
  const [count, setCount] = useState(0);

  return (
    <>
      <h2>App Count Button 1</h2>
      <Button onClick={() => setCount(count + 1)}>
        Count: {count}
      </Button>
    </>
  );
}
