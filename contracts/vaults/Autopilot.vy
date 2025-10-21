#    ________   __  __   _________  ______   ______   ________  __       ______   _________  
#   /_______/\ /_/\/_/\ /________/\/_____/\ /_____/\ /_______/\/_/\     /_____/\ /________/\ 
#   \::: _  \ \\:\ \:\ \\__.::.__\/\:::_ \ \\:::_ \ \\__.::._\/\:\ \    \:::_ \ \\__.::.__\/ 
#    \::(_)  \ \\:\ \:\ \  \::\ \   \:\ \ \ \\:(_) \ \  \::\ \  \:\ \    \:\ \ \ \  \::\ \   
#     \:: __  \ \\:\ \:\ \  \::\ \   \:\ \ \ \\: ___\/  _\::\ \__\:\ \____\:\ \ \ \  \::\ \  
#      \:.\ \  \ \\:\_\:\ \  \::\ \   \:\_\ \ \\ \ \   /__\::\__/\\:\/___/\\:\_\ \ \  \::\ \ 
#       \__\/\__\/ \_____\/   \__\/    \_____\/ \_\/   \________\/ \_____\/ \_____\/   \__\/ 
#                                                                       
#     ╔══════════════════════════════════════════════════╗
#     ║  ** Earn Autopilot Vaults **                     ║
#     ║  Managed by AI agents, enforced by onchain rules ║
#     ╚══════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

exports: earnVault.__interface__
initializes: earnVault
from contracts.vaults.modules import EarnVault as earnVault

@deploy
def __init__(
    _asset: address,
    _name: String[64],
    _symbol: String[32],
    _undyHq: address,
    _minHqTimeLock: uint256,
    _maxHqTimeLock: uint256,
    _startingAgent: address,
):
    earnVault.__init__(
        _asset,
        _name,
        _symbol,
        _undyHq,
        _minHqTimeLock,
        _maxHqTimeLock,
        _startingAgent,
    )
