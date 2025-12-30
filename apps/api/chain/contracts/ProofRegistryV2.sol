// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ProofRegistryV2
/// @notice Anchors a stable media identifier that survives platform edits.
///         - Primary key: mediaId (bytes32)
///         - Also stores the exact original file SHA-256 (bytes32) for "exact original" proof.
contract ProofRegistryV2 {
    struct Record {
        bytes32 ownerSha;     // sha256(email) or other owner identity hash
        bytes32 fileSha256;   // exact original file SHA-256 (optional: 0x0 if not provided)
        string  ipfsCid;      // optional off-chain pointer (can be empty)
        uint256 timestamp;    // block timestamp when registered
        address submitter;    // msg.sender who registered
    }

    /// mediaId => Record
    mapping(bytes32 => Record) private byMediaId;

    /// Optional reverse index: exact file hash -> mediaId
    mapping(bytes32 => bytes32) public mediaIdByFileSha;

    event Registered(
        bytes32 indexed mediaId,
        bytes32 indexed ownerSha,
        bytes32 fileSha256,
        string  ipfsCid,
        address indexed submitter,
        uint256 blockNumber
    );

    /// @notice Register a mediaId once. Cannot be overwritten.
    function register(
        bytes32 mediaId,
        bytes32 ownerSha,
        bytes32 fileSha256,
        string calldata ipfsCid
    ) external {
        require(mediaId != bytes32(0), "mediaId required");
        Record storage r = byMediaId[mediaId];
        require(r.timestamp == 0, "already registered");

        r.ownerSha   = ownerSha;
        r.fileSha256 = fileSha256;
        r.ipfsCid    = ipfsCid;
        r.timestamp  = block.timestamp;
        r.submitter  = msg.sender;

        if (fileSha256 != bytes32(0) && mediaIdByFileSha[fileSha256] == bytes32(0)) {
            mediaIdByFileSha[fileSha256] = mediaId;
        }

        emit Registered(mediaId, ownerSha, fileSha256, ipfsCid, msg.sender, block.number);
    }

    /// @notice Get record by mediaId.
    function getByMediaId(bytes32 mediaId)
        external
        view
        returns (
            bool exists,
            bytes32 ownerSha,
            bytes32 fileSha256,
            string memory ipfsCid,
            uint256 timestamp,
            address submitter
        )
    {
        Record storage r = byMediaId[mediaId];
        if (r.timestamp == 0) {
            return (false, bytes32(0), bytes32(0), "", 0, address(0));
        }
        return (true, r.ownerSha, r.fileSha256, r.ipfsCid, r.timestamp, r.submitter);
    }

    /// @notice Optional helper: look up a mediaId by exact original file hash (if it was provided).
    function getByFileSha(bytes32 fileSha256)
        external
        view
        returns (bool exists, bytes32 mediaId)
    {
        bytes32 m = mediaIdByFileSha[fileSha256];
        return (m != bytes32(0), m);
    }
}
