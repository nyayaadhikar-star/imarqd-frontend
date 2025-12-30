// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ProofRegistry {
    struct Proof {
        bool exists;
        bytes32 ownerEmailSha;
        uint256 timestamp;
        string ipfsCid;
    }

    mapping(bytes32 => Proof) private proofs;

    event ProofRegistered(bytes32 indexed fileHash, bytes32 indexed emailSha, string ipfsCid, uint256 timestamp);

    function registerProof(bytes32 fileHash, bytes32 emailSha, string calldata ipfsCid) external {
        require(!proofs[fileHash].exists, "Already registered");
        proofs[fileHash] = Proof(true, emailSha, block.timestamp, ipfsCid);
        emit ProofRegistered(fileHash, emailSha, ipfsCid, block.timestamp);
    }

    function getProof(bytes32 fileHash)
        external
        view
        returns (bool exists, bytes32 ownerEmailSha, uint256 timestamp, string memory ipfsCid)
    {
        Proof memory p = proofs[fileHash];
        return (p.exists, p.ownerEmailSha, p.timestamp, p.ipfsCid);
    }
}
