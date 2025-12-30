import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import "@nomicfoundation/hardhat-verify";
import * as dotenv from "dotenv";
import { resolve } from "path";
import { existsSync, mkdirSync } from "fs";

dotenv.config({ path: resolve(__dirname, "../.env") });

const ABI_OUT_DIR = resolve(__dirname, "../src/app/services/blockchain/abi");
if (!existsSync(ABI_OUT_DIR)) mkdirSync(ABI_OUT_DIR, { recursive: true });

const AMOY_RPC = process.env.AMOY_RPC_URL || process.env.WEB3_RPC_URL || "";
const PRIVATE_KEY = (process.env.WEB3_PRIVATE_KEY || "").trim();

if (!/^0x[a-fA-F0-9]{64}$/.test(PRIVATE_KEY)) {
  console.error("\n[Hardhat] WEB3_PRIVATE_KEY is missing/invalid. Export it from MetaMask (0x + 64 hex).");
  process.exit(1);
}
if (!AMOY_RPC) {
  console.error("\n[Hardhat] AMOY_RPC_URL / WEB3_RPC_URL missing. Set https://rpc-amoy.polygon.technology/ or a provider URL.");
  process.exit(1);
}

const config: HardhatUserConfig = {
  solidity: {
  compilers: [
    { version: "0.8.24", settings: { optimizer: { enabled: true, runs: 200 } } },
    { version: "0.8.20", settings: { optimizer: { enabled: true, runs: 200 } } },
  ],
  overrides: {
    "contracts/ProofRegistryV2.sol": { version: "0.8.24" },
    "contracts/ProofRegistry.sol":  { version: "0.8.20" }, // if old one needs it
  },
},
  networks: {
    amoy: {
      url: AMOY_RPC,
      accounts: [PRIVATE_KEY],
      chainId: 80002
    }
  },
  etherscan: {
    apiKey: { polygonAmoy: process.env.POLYGONSCAN_API_KEY || "" },
    customChains: [{
      network: "polygonAmoy",
      chainId: 80002,
      urls: { apiURL: "https://api-amoy.polygonscan.com/api", browserURL: "https://amoy.polygonscan.com" }
    }]
  },
  paths: {
    // you chose Option B earlier:
    root:      resolve(__dirname, ".."), // apps/api
    // sources:   resolve(__dirname, "../src/app/services/blockchain/contracts"),
    sources: resolve(__dirname, "./contracts"),
    tests:     resolve(__dirname, "./test"),
    artifacts: resolve(__dirname, "./artifacts"),
    cache:     resolve(__dirname, "./cache")
  }
};
export default config;
