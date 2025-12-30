import { artifacts, ethers, network, run } from "hardhat";
import { writeFileSync, mkdirSync } from "fs";
import { resolve, dirname } from "path";

async function main() {
  const [deployer] = await ethers.getSigners();
  const addr = await deployer.getAddress();
  const bal = await deployer.provider!.getBalance(addr);

  console.log("Deployer:", addr);
  console.log("Balance:", bal.toString());

  console.log("\n🔧 Network:", network.name);

  const Factory = await ethers.getContractFactory("ProofRegistry");
  console.log("⏳ Deploying ProofRegistry...");
  const contract = await Factory.deploy();
  await contract.waitForDeployment();

  const deployedAt = await contract.getAddress();
  console.log("✅ Deployed at:", deployedAt);

  // --- Write ABI and address into the API tree ---
  // __dirname => apps/api/chain/scripts
  const ABI_DIR = resolve(__dirname, "..", "..", "src", "app", "services", "blockchain", "abi");
  mkdirSync(ABI_DIR, { recursive: true });

  const artifact = await artifacts.readArtifact("ProofRegistry");
  const abiPath = resolve(ABI_DIR, "ProofRegistry.json");
  writeFileSync(abiPath, JSON.stringify(artifact, null, 2), "utf-8");

  const abiBytes = Buffer.byteLength(JSON.stringify(artifact));
  console.log("📝 ABI written:", abiPath, "bytes=", abiBytes);
  if (abiBytes < 200) {
    throw new Error("ABI write looks empty/suspicious. Aborting to avoid broken backend.");
  }

  const addrPath = resolve(ABI_DIR, "ProofRegistry.address.json");
  writeFileSync(
    addrPath,
    JSON.stringify({ address: deployedAt, network: network.name, chainId: network.config.chainId }, null, 2),
    "utf-8"
  );
  console.log("🗂  Address written:", addrPath);

  // Optional verify (skips if no key configured)
  try {
    console.log("ℹ️ Waiting a few blocks before verify...");
    await contract.deploymentTransaction()?.wait(3);
    await run("verify:verify", {
      address: deployedAt,
      constructorArguments: [],
    });
    console.log("🔍 Verified on explorer.");
  } catch (e: any) {
    console.log("ℹ️ Verify skipped or already verified:", e?.message || e);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
