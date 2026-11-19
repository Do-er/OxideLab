// Copyright (C) 2026 AnalyseDeCircuit
// SPDX-License-Identifier: GPL-3.0-only

use clap::{Args, Subcommand};

#[derive(Debug, Args)]
#[command(
    long_about = "Bridge MCP JSON-RPC on standard input/output to the running OxideLab loopback endpoint. The bearer credential is read from an environment variable and is never accepted as a command-line argument."
)]
#[command(
    after_help = "Example:\n  OXIDELAB_MCP_TOKEN=... oxidelab mcp bridge\n\nSet OXIDELAB_MCP_ENDPOINT only when automatic endpoint discovery is unavailable."
)]
pub struct McpCommand {
    #[command(subcommand)]
    pub action: McpAction,
}

#[derive(Debug, Subcommand)]
pub enum McpAction {
    #[command(about = "Bridge stdio MCP messages to the running OxideLab app")]
    Bridge(McpBridgeArgs),
}

#[derive(Debug, Args)]
pub struct McpBridgeArgs {
    #[arg(
        long,
        env = "OXIDELAB_MCP_ENDPOINT",
        help = "Override the discovered loopback MCP endpoint"
    )]
    pub endpoint: Option<String>,
    #[arg(
        long,
        default_value = "OXIDELAB_MCP_TOKEN",
        value_name = "NAME",
        help = "Read the bearer credential from environment variable NAME"
    )]
    pub token_env: String,
}
