import { ethers, artifacts, network } from "hardhat";
import fs from "fs";
import path from "path";

async function main() {
  console.log("🔧 Network:", network.name);

  const [deployer] = await ethers.getSigners();
  const balance = await deployer.provider!.getBalance(deployer.address);
  console.log("Deployer:", deployer.address);
  console.log("Balance:", balance.toString());

  // ---- Try to locate the artifact by FQN or by simple name ----
  // Expected file location & contract name:
  const fqn = "contracts/ProofRegistryV2.sol:ProofRegistryV2";

  // Sanity: show what Hardhat thinks exists
  const all = await artifacts.getAllFullyQualifiedNames();
  const hasFqn = all.includes(fqn);
  const hasSimple = all.some((n) => n.endsWith(":ProofRegistryV2"));

  if (!hasFqn && !hasSimple) {
    console.log("Available artifacts:");
    all.forEach((n) => console.log(" -", n));
    throw new Error(
      `Artifact not found for ProofRegistryV2.\n` +
      `Expected FQN: ${fqn}\n` +
      `Ensure the file is apps/api/chain/contracts/ProofRegistryV2.sol and contract name is 'ProofRegistryV2'.`
    );
  }

  const factory = await ethers.getContractFactory(hasFqn ? fqn : "ProofRegistryV2");

  console.log("🚀 Deploying ProofRegistryV2...");
  const contract = await factory.deploy();
  await contract.waitForDeployment();
  const address = await contract.getAddress();
  console.log("✅ Deployed at:", address);

  // Write ABI & address into the API folder for backend use
  const artifact = await artifacts.readArtifact(hasFqn ? fqn : "ProofRegistryV2");

  const apiAbiDir = path.resolve(__dirname, "../../src/app/services/blockchain/abi");
  if (!fs.existsSync(apiAbiDir)) fs.mkdirSync(apiAbiDir, { recursive: true });

  const outAbi = path.join(apiAbiDir, "ProofRegistryV2.json");
  fs.writeFileSync(outAbi, JSON.stringify(artifact, null, 2));
  console.log("📝 ABI written:", outAbi, "bytes", fs.statSync(outAbi).size);

  const outAddr = path.join(apiAbiDir, "ProofRegistryV2.address.json");
  fs.writeFileSync(outAddr, JSON.stringify({ network: network.name, address }, null, 2));
  console.log("📝 Address written:", outAddr);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
