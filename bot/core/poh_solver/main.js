const d2601c1d81d312e2edcccde782150cce47a66c30 = require("./wasm_handler.js");
const { TextDecoder, TextEncoder } = require('util');

const textDecoder = new TextDecoder();
const textEncoder = new TextEncoder();

async function main() {
    await d2601c1d81d312e2edcccde782150cce47a66c30.wasm_init("bot/core/poh_solver/magic.wasm");

    const input = process.argv[2];
    if (!input) {
        console.error("Please provide input as a comma-separated string.");
        process.exit(1);
    }

    const parsedData = JSON.parse(textDecoder.decode(new Uint8Array(input.split(',').map(x => parseInt(x)))));

    const result = await d2601c1d81d312e2edcccde782150cce47a66c30.e12f1e505654847829d9ae61aab7527dd0fd884(parsedData['a'], parsedData['b']);

    const encodedResult = String(textEncoder.encode(JSON.stringify(result)));

    console.log(encodedResult);
}

main().catch(err => {
    console.error("Error:", err);
});
