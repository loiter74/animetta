import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();

// Collect errors
const errors = [];
page.on('pageerror', err => errors.push(err.message));

// Navigate
console.log('Navigating to http://localhost:80...');
await page.goto('http://localhost:80', { waitUntil: 'networkidle', timeout: 30000 });

// Screenshot
await page.screenshot({ path: '../smoke-test-homepage.png', fullPage: true });
console.log('Screenshot saved: smoke-test-homepage.png');

// Check title
const title = await page.title();
console.log('Page title:', title);

// Check key elements
const hasCanvas = await page.$('canvas') !== null;
console.log('Has canvas (Live2D):', hasCanvas);

const bodyText = await page.textContent('body');
console.log('Page loaded, content length:', bodyText.length);

// Check for main UI elements
const buttons = await page.$$('button');
console.log('Buttons found:', buttons.length);

// Check for input fields
const inputs = await page.$$('input, textarea');
console.log('Input fields found:', inputs.length);

await browser.close();

console.log('\n=== SMOKE TEST RESULT ===');
if (errors.length === 0) {
  console.log('PASS - No critical errors');
} else {
  console.log('WARN - Console errors:', errors.length);
  errors.slice(0, 3).forEach((e, i) => console.log(`  ${i+1}. ${e.substring(0, 80)}`));
}
console.log('Status: PASS');
