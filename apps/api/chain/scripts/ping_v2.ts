import { ethers } from "hardhat";

async function main() {
  const addr = "<PASTE_V2_ADDRESS>";
  const c = await ethers.getContractAt("ProofRegistryV2", addr);

  const mediaId = ethers.keccak256(ethers.toUtf8Bytes("demo-media-1"));
  const ownerSha = "0x" + "11".repeat(32);
  const fileSha  = "0x" + "22".repeat(32);

  const tx = await c.register(mediaId, ownerSha, fileSha, "");
  const rc = await tx.wait();
  console.log("Registered in block", rc?.blockNumber);

  const r = await c.getByMediaId(mediaId);
  console.log("getByMediaId ->", r);
}

main().catch(console.error);
