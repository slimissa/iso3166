# iso3166-registry (JavaScript)

JavaScript wrapper for the [ISO 3166 country registry](https://github.com/slimissa/iso3166).

## Install

From the repository:

```bash
npm install ./wrappers/javascript
```

Zero runtime dependencies. Requires Node 18 or newer for the built-in
test runner (the library itself works on Node 12+).

Publication to npm is tracked for v1.2.0.
Library
```javascript

const { CountryRegistry } = require("iso3166-registry");

const reg = new CountryRegistry();

const us = reg.active("US");
console.log(us.alpha_3, us.name);                // USA United States of America

console.log(reg.byNumeric("840").alpha_2);       // US
console.log(reg.byAlpha3("GBR").name);           // United Kingdom ...

console.log(reg.region("Europe").length);        // number of European entries
console.log(reg.search("united").length);
console.log(reg.summary());
```

active() returns null for an unknown code. Use withAlpha2() to
retrieve both the active and withdrawn entries for a reassigned code
such as AI or SK.
Tests
```bash

npm test
```
License

Apache 2.0.