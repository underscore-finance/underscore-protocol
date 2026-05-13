# Mutability Scanner Inventory

## Counts

- vyper_files: 95
- defs: 2490
- view: 1119
- pure: 169
- nonreentrant: 33

## view-revert (0)

- none

## can-be-view (8)

- contracts/mock/MockRipe.vy:377 deleverageForWithdrawal [exempt: mock matches mutating Ripe deleverage interface]
- contracts/mock/MockYieldLego.vy:730 setMorphoRewardsAddr [exempt: mock keeps mutating rewards setter interface]
- contracts/mock/MockYieldLego.vy:737 setEulerRewardsAddr [exempt: mock keeps mutating rewards setter interface]
- contracts/mock/MockYieldLego.vy:744 setCompRewardsAddr [exempt: mock keeps mutating rewards setter interface]
- contracts/vaults/modules/EarnVaultWallet.vy:381 _validateAndGetSwapInfo [exempt: preserving exported vault runtime under EIP-170]
- contracts/vaults/modules/EarnVaultWallet.vy:862 _canManagerPerformAction [exempt: preserving shared manager asserts keeps exported vault runtime under EIP-170]
- contracts/vaults/modules/LevgVaultWallet.vy:977 _canManagerPerformAction [exempt: preserving shared manager asserts keeps exported vault runtime under EIP-170]
- contracts/vaults/modules/VaultErc20Token.vy:216 _validateNewApprovals [exempt: preserving shared approval asserts keeps exported vault runtime under EIP-170]

## view-could-be-pure (0)

- none

## interface-mismatch (0)

- none

## invalid-exemption (0)

- none

## interface-ambiguous (107)

- contracts/config/SwitchboardAlpha.vy:41 MissionControl.userWalletConfig -> contracts/config/DefaultsBase.vy:35 (view), contracts/config/DefaultsLocal.vy:41 (view)
- contracts/config/SwitchboardAlpha.vy:42 MissionControl.agentConfig -> contracts/config/DefaultsBase.vy:67 (view), contracts/config/DefaultsLocal.vy:73 (view)
- contracts/config/SwitchboardBravo.vy:34 UndyEcoContract.recoverFundsMany -> contracts/modules/DeptBasics.vy:69 (nonpayable), contracts/modules/DexLegoData.vy:74 (nonpayable), contracts/modules/YieldLegoData.vy:329 (nonpayable), contracts/registries/UndyHq.vy:367 (nonpayable)
- contracts/config/SwitchboardBravo.vy:35 UndyEcoContract.recoverNft -> contracts/core/userWallet/UserWallet.vy:1421 (nonpayable), contracts/core/userWallet/UserWalletConfig.vy:844 (nonpayable), contracts/legos/dexes/AeroSlipstream.vy:1172 (nonpayable), contracts/legos/dexes/UniswapV3.vy:1163 (nonpayable)
- contracts/config/SwitchboardBravo.vy:36 UndyEcoContract.recoverFunds -> contracts/modules/DeptBasics.vy:63 (nonpayable), contracts/modules/DexLegoData.vy:68 (nonpayable), contracts/modules/YieldLegoData.vy:323 (nonpayable), contracts/registries/UndyHq.vy:361 (nonpayable)
- contracts/config/SwitchboardBravo.vy:37 UndyEcoContract.pause -> contracts/modules/DeptBasics.vy:52 (nonpayable), contracts/modules/DexLegoData.vy:57 (nonpayable), contracts/modules/Erc20Token.vy:612 (nonpayable), contracts/modules/YieldLegoData.vy:312 (nonpayable), contracts/vaults/modules/VaultErc20Token.vy:371 (nonpayable)
- contracts/config/SwitchboardCharlie.vy:57 LevgVault.removeManager -> contracts/core/userWallet/UserWalletConfig.vy:580 (nonpayable), contracts/vaults/modules/EarnVaultWallet.vy:912 (nonpayable), contracts/vaults/modules/LevgVaultWallet.vy:1027 (nonpayable)
- contracts/config/SwitchboardCharlie.vy:59 LevgVault.addManager -> contracts/vaults/modules/EarnVaultWallet.vy:890 (nonpayable), contracts/vaults/modules/LevgVaultWallet.vy:1005 (nonpayable)
- contracts/config/SwitchboardCharlie.vy:64 YieldLego.deregisterVaultTokenLocally -> contracts/legos/RipeLego.vy:501 (nonpayable), contracts/legos/UnderscoreLego.vy:396 (nonpayable), contracts/legos/yield/40Acres.vy:424 (nonpayable), contracts/legos/yield/AaveV3.vy:429 (nonpayable), contracts/legos/yield/Avantis.vy:420 (nonpayable), contracts/legos/yield/CompoundV3.vy:421 (nonpayable), contracts/legos/yield/Euler.vy:437 (nonpayable), contracts/legos/yield/ExtraFi.vy:442 (nonpayable), contracts/legos/yield/Fluid.vy:481 (nonpayable), contracts/legos/yield/Moonwell.vy:448 (nonpayable), contracts/legos/yield/Morpho.vy:527 (nonpayable), contracts/legos/yield/SkyPsm.vy:412 (nonpayable), contracts/legos/yield/Wasabi.vy:481 (nonpayable), contracts/mock/MockYieldLego.vy:355 (nonpayable)
- contracts/config/SwitchboardCharlie.vy:65 YieldLego.registerVaultTokenLocally -> contracts/legos/RipeLego.vy:480 (nonpayable), contracts/legos/UnderscoreLego.vy:375 (nonpayable), contracts/legos/yield/40Acres.vy:403 (nonpayable), contracts/legos/yield/AaveV3.vy:408 (nonpayable), contracts/legos/yield/Avantis.vy:399 (nonpayable), contracts/legos/yield/CompoundV3.vy:400 (nonpayable), contracts/legos/yield/Euler.vy:416 (nonpayable), contracts/legos/yield/Fluid.vy:460 (nonpayable), contracts/legos/yield/Moonwell.vy:427 (nonpayable), contracts/legos/yield/Morpho.vy:506 (nonpayable), contracts/legos/yield/SkyPsm.vy:389 (nonpayable), contracts/legos/yield/Wasabi.vy:460 (nonpayable), contracts/mock/MockYieldLego.vy:334 (nonpayable)
- contracts/config/SwitchboardCharlie.vy:66 YieldLego.canRegisterVaultToken -> contracts/legos/RipeLego.vy:464 (view), contracts/legos/UnderscoreLego.vy:357 (view), contracts/legos/yield/40Acres.vy:387 (view), contracts/legos/yield/AaveV3.vy:389 (view), contracts/legos/yield/Avantis.vy:383 (view), contracts/legos/yield/CompoundV3.vy:382 (view), contracts/legos/yield/Euler.vy:398 (view), contracts/legos/yield/ExtraFi.vy:397 (view), contracts/legos/yield/Fluid.vy:441 (view), contracts/legos/yield/Moonwell.vy:408 (view), contracts/legos/yield/Morpho.vy:487 (view), contracts/legos/yield/SkyPsm.vy:373 (view), contracts/legos/yield/Wasabi.vy:442 (view), contracts/mock/MockYieldLego.vy:318 (view)
- contracts/config/SwitchboardCharlie.vy:69 YieldLego.addPriceSnapshot -> contracts/legos/RipeLego.vy:532 (nonpayable), contracts/legos/UnderscoreLego.vy:441 (nonpayable), contracts/legos/yield/40Acres.vy:469 (nonpayable), contracts/legos/yield/AaveV3.vy:612 (nonpayable), contracts/legos/yield/Avantis.vy:462 (nonpayable), contracts/legos/yield/CompoundV3.vy:701 (nonpayable), contracts/legos/yield/Euler.vy:482 (nonpayable), contracts/legos/yield/ExtraFi.vy:499 (nonpayable), contracts/legos/yield/Fluid.vy:526 (nonpayable), contracts/legos/yield/Moonwell.vy:493 (nonpayable), contracts/legos/yield/Morpho.vy:572 (nonpayable), contracts/legos/yield/SkyPsm.vy:459 (nonpayable), contracts/legos/yield/Wasabi.vy:526 (nonpayable), contracts/mock/MockRipe.vy:259 (nonpayable), contracts/mock/MockYieldLego.vy:386 (nonpayable)
- contracts/config/SwitchboardCharlie.vy:70 YieldLego.setMorphoRewardsAddr -> contracts/legos/yield/Morpho.vy:766 (nonpayable), contracts/mock/MockYieldLego.vy:730 (nonpayable)
- contracts/config/SwitchboardCharlie.vy:71 YieldLego.setEulerRewardsAddr -> contracts/legos/yield/Euler.vy:680 (nonpayable), contracts/mock/MockYieldLego.vy:737 (nonpayable)
- contracts/config/SwitchboardCharlie.vy:72 YieldLego.setCompRewardsAddr -> contracts/legos/yield/CompoundV3.vy:687 (nonpayable), contracts/mock/MockYieldLego.vy:744 (nonpayable)
- contracts/config/SwitchboardCharlie.vy:81 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/config/SwitchboardCharlie.vy:84 EarnVault.sweepLeftovers -> contracts/vaults/EarnVault.vy:554 (nonpayable), contracts/vaults/LevgVault.vy:473 (nonpayable)
- contracts/core/Appraiser.vy:36 RipePriceDesk.addPriceSnapshot -> contracts/legos/RipeLego.vy:532 (nonpayable), contracts/legos/UnderscoreLego.vy:441 (nonpayable), contracts/legos/yield/40Acres.vy:469 (nonpayable), contracts/legos/yield/AaveV3.vy:612 (nonpayable), contracts/legos/yield/Avantis.vy:462 (nonpayable), contracts/legos/yield/CompoundV3.vy:701 (nonpayable), contracts/legos/yield/Euler.vy:482 (nonpayable), contracts/legos/yield/ExtraFi.vy:499 (nonpayable), contracts/legos/yield/Fluid.vy:526 (nonpayable), contracts/legos/yield/Moonwell.vy:493 (nonpayable), contracts/legos/yield/Morpho.vy:572 (nonpayable), contracts/legos/yield/SkyPsm.vy:459 (nonpayable), contracts/legos/yield/Wasabi.vy:526 (nonpayable), contracts/mock/MockRipe.vy:259 (nonpayable), contracts/mock/MockYieldLego.vy:386 (nonpayable)
- contracts/core/Appraiser.vy:51 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/core/Billing.vy:42 UserWalletConfig.deregisterAsset -> contracts/core/userWallet/UserWallet.vy:1301 (nonpayable), contracts/core/userWallet/UserWalletConfig.vy:834 (nonpayable)
- contracts/core/LootDistributor.vy:67 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/core/agent/AgentSenderSpecial.vy:34 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/core/agent/AgentWrapper.vy:42 UndyHq.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/core/agent/LevgVaultAgent.vy:27 RipeLego.deleverageUser -> contracts/legos/RipeLego.vy:971 (nonpayable), contracts/mock/MockRipe.vy:382 (nonpayable)
- contracts/core/agent/LevgVaultAgent.vy:30 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/core/userWallet/UserWallet.vy:61 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/core/userWallet/UserWalletConfig.vy:38 UserWallet.withdrawFromYield -> contracts/core/userWallet/UserWallet.vy:298 (nonpayable), contracts/vaults/modules/EarnVaultWallet.vy:245 (nonpayable), contracts/vaults/modules/LevgVaultWallet.vy:284 (nonpayable)
- contracts/core/userWallet/UserWalletConfig.vy:41 UserWallet.recoverNft -> contracts/core/userWallet/UserWallet.vy:1421 (nonpayable), contracts/legos/dexes/AeroSlipstream.vy:1172 (nonpayable), contracts/legos/dexes/UniswapV3.vy:1163 (nonpayable)
- contracts/core/userWallet/UserWalletConfig.vy:50 Sentinel.checkManagerLimitsPostTx -> contracts/core/walletBackpack/Sentinel.vy:257 (view), contracts/mock/MockSentinel.vy:55 (view)
- contracts/core/userWallet/UserWalletConfig.vy:51 Sentinel.canSignerPerformActionWithConfig -> contracts/core/walletBackpack/Sentinel.vy:72 (view), contracts/mock/MockSentinel.vy:19 (view)
- contracts/core/userWallet/UserWalletConfig.vy:52 Sentinel.isValidPayeeAndGetData -> contracts/core/walletBackpack/Sentinel.vy:448 (view), contracts/mock/MockSentinel.vy:37 (view)
- contracts/core/userWallet/UserWalletConfig.vy:53 Sentinel.isValidChequeAndGetData -> contracts/core/walletBackpack/Sentinel.vy:651 (view), contracts/mock/MockSentinel.vy:78 (view)
- contracts/core/userWallet/UserWalletConfig.vy:64 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/core/userWallet/UserWalletConfig.vy:65 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/core/walletBackpack/ChequeBook.vy:47 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/core/walletBackpack/HighCommand.vy:29 UserWalletConfig.removeManager -> contracts/core/userWallet/UserWalletConfig.vy:580 (nonpayable), contracts/vaults/modules/EarnVaultWallet.vy:912 (nonpayable), contracts/vaults/modules/LevgVaultWallet.vy:1027 (nonpayable)
- contracts/core/walletBackpack/HighCommand.vy:35 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/core/walletBackpack/Kernel.vy:44 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/core/walletBackpack/Migrator.vy:34 UserWalletConfig.deregisterAsset -> contracts/core/userWallet/UserWallet.vy:1301 (nonpayable), contracts/core/userWallet/UserWalletConfig.vy:834 (nonpayable)
- contracts/core/walletBackpack/Migrator.vy:59 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/core/walletBackpack/Paymaster.vy:48 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/data/MissionControl.vy:33 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/helpers/LevgVaultTools.vy:18 LevgVault.convertToAssetsSafe -> contracts/vaults/EarnVault.vy:482 (view), contracts/vaults/LevgVault.vy:401 (view)
- contracts/helpers/LevgVaultTools.vy:19 LevgVault.getTotalAssets -> contracts/vaults/EarnVault.vy:90 (view), contracts/vaults/LevgVault.vy:98 (view)
- contracts/helpers/LevgVaultTools.vy:29 RipeCreditEngine.getUserDebtAmount -> contracts/legos/RipeLego.vy:1018 (view), contracts/mock/MockRipe.vy:311 (view)
- contracts/helpers/LevgVaultTools.vy:37 YieldLego.getUnderlyingAmountSafe -> contracts/legos/RipeLego.vy:293 (view), contracts/legos/UnderscoreLego.vy:186 (view), contracts/legos/yield/40Acres.vy:186 (view), contracts/legos/yield/AaveV3.vy:201 (view), contracts/legos/yield/Avantis.vy:183 (view), contracts/legos/yield/CompoundV3.vy:203 (view), contracts/legos/yield/Euler.vy:209 (view), contracts/legos/yield/ExtraFi.vy:196 (view), contracts/legos/yield/Fluid.vy:234 (view), contracts/legos/yield/Moonwell.vy:223 (view), contracts/legos/yield/Morpho.vy:231 (view), contracts/legos/yield/SkyPsm.vy:201 (view), contracts/legos/yield/Wasabi.vy:188 (view), contracts/mock/MockYieldLego.vy:142 (view)
- contracts/helpers/LevgVaultTools.vy:38 YieldLego.getUnderlyingAmount -> contracts/legos/RipeLego.vy:278 (view), contracts/legos/UnderscoreLego.vy:171 (view), contracts/legos/yield/40Acres.vy:171 (view), contracts/legos/yield/AaveV3.vy:185 (view), contracts/legos/yield/Avantis.vy:168 (view), contracts/legos/yield/CompoundV3.vy:187 (view), contracts/legos/yield/Euler.vy:194 (view), contracts/legos/yield/ExtraFi.vy:178 (view), contracts/legos/yield/Fluid.vy:219 (view), contracts/legos/yield/Moonwell.vy:208 (view), contracts/legos/yield/Morpho.vy:216 (view), contracts/legos/yield/SkyPsm.vy:183 (view), contracts/legos/yield/Wasabi.vy:170 (view), contracts/mock/MockYieldLego.vy:120 (view)
- contracts/helpers/LevgVaultTools.vy:54 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/legos/LegoTools.vy:34 LegoDexNonStandard.getSwapAmountOut -> contracts/legos/dexes/AeroClassic.vy:621 (view), contracts/legos/dexes/AeroSlipstream.vy:947 (nonpayable), contracts/legos/dexes/Curve.vy:1098 (view), contracts/legos/dexes/UniswapV2.vy:549 (view), contracts/legos/dexes/UniswapV3.vy:937 (nonpayable), contracts/mock/MockDexLego.vy:547 (pure), contracts/mock/MockSwapLego.vy:305 (pure)
- contracts/legos/LegoTools.vy:35 LegoDexNonStandard.getSwapAmountIn -> contracts/legos/dexes/AeroClassic.vy:646 (view), contracts/legos/dexes/AeroSlipstream.vy:999 (nonpayable), contracts/legos/dexes/Curve.vy:1132 (view), contracts/legos/dexes/UniswapV2.vy:571 (view), contracts/legos/dexes/UniswapV3.vy:989 (nonpayable), contracts/mock/MockDexLego.vy:564 (pure), contracts/mock/MockSwapLego.vy:322 (pure)
- contracts/legos/LegoTools.vy:36 LegoDexNonStandard.getBestSwapAmountIn -> contracts/legos/dexes/AeroClassic.vy:632 (view), contracts/legos/dexes/AeroSlipstream.vy:971 (nonpayable), contracts/legos/dexes/Curve.vy:1114 (view), contracts/legos/dexes/UniswapV2.vy:561 (view), contracts/legos/dexes/UniswapV3.vy:961 (nonpayable), contracts/mock/MockDexLego.vy:558 (pure), contracts/mock/MockSwapLego.vy:316 (pure)
- contracts/legos/LegoTools.vy:37 LegoDexNonStandard.getBestSwapAmountOut -> contracts/legos/dexes/AeroClassic.vy:590 (view), contracts/legos/dexes/AeroSlipstream.vy:922 (nonpayable), contracts/legos/dexes/Curve.vy:1077 (view), contracts/legos/dexes/UniswapV2.vy:539 (view), contracts/legos/dexes/UniswapV3.vy:911 (nonpayable), contracts/mock/MockDexLego.vy:541 (pure), contracts/mock/MockSwapLego.vy:299 (pure)
- contracts/legos/LegoTools.vy:42 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/legos/RipeLego.vy:61 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/legos/RipeLego.vy:62 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/UnderscoreLego.vy:52 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/dexes/AeroClassic.vy:63 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/dexes/AeroSlipstream.vy:54 AeroNftPositionManager.burn -> contracts/mock/MockErc20.vy:144 (nonpayable), contracts/modules/Erc20Token.vy:326 (nonpayable), contracts/vaults/modules/VaultErc20Token.vy:247 (nonpayable)
- contracts/legos/dexes/AeroSlipstream.vy:77 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/dexes/Curve.vy:128 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/dexes/UniswapV2.vy:58 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/dexes/UniswapV3.vy:54 UniV3NftPositionManager.burn -> contracts/mock/MockErc20.vy:144 (nonpayable), contracts/modules/Erc20Token.vy:326 (nonpayable), contracts/vaults/modules/VaultErc20Token.vy:247 (nonpayable)
- contracts/legos/dexes/UniswapV3.vy:78 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/yield/40Acres.vy:46 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/yield/AaveV3.vy:53 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/yield/Avantis.vy:46 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/yield/CompoundV3.vy:56 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/yield/Euler.vy:50 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/yield/ExtraFi.vy:54 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/yield/Fluid.vy:50 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/yield/Moonwell.vy:59 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/yield/Morpho.vy:56 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/yield/SkyPsm.vy:41 SkyPsm.totalAssets -> contracts/mock/Mock40AcresVault.vy:110 (view), contracts/mock/MockErc4626Vault.vy:108 (view), contracts/vaults/EarnVault.vy:79 (view), contracts/vaults/LevgVault.vy:92 (view)
- contracts/legos/yield/SkyPsm.vy:52 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/legos/yield/Wasabi.vy:46 Registry.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/mock/MockDexLego.vy:21 MockToken.mint -> contracts/mock/MockErc20.vy:114 (nonpayable), contracts/tokens/UndyToken.vy:63 (nonpayable)
- contracts/mock/MockDexLego.vy:22 MockToken.burn -> contracts/mock/MockErc20.vy:144 (nonpayable), contracts/modules/Erc20Token.vy:326 (nonpayable), contracts/vaults/modules/VaultErc20Token.vy:247 (nonpayable)
- contracts/mock/MockRipe.vy:8 MockToken.mint -> contracts/mock/MockErc20.vy:114 (nonpayable), contracts/tokens/UndyToken.vy:63 (nonpayable)
- contracts/mock/MockRipe.vy:9 MockToken.burn -> contracts/mock/MockErc20.vy:144 (nonpayable), contracts/modules/Erc20Token.vy:326 (nonpayable), contracts/vaults/modules/VaultErc20Token.vy:247 (nonpayable)
- contracts/mock/MockSwapLego.vy:21 MockToken.mint -> contracts/mock/MockErc20.vy:114 (nonpayable), contracts/tokens/UndyToken.vy:63 (nonpayable)
- contracts/mock/MockSwapLego.vy:22 MockToken.burn -> contracts/mock/MockErc20.vy:144 (nonpayable), contracts/modules/Erc20Token.vy:326 (nonpayable), contracts/vaults/modules/VaultErc20Token.vy:247 (nonpayable)
- contracts/modules/Addys.vy:6 UndyHq.isValidAddr -> contracts/mock/MockRipe.vy:72 (pure), contracts/modules/AddressRegistry.vy:479 (view)
- contracts/modules/Addys.vy:7 UndyHq.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/modules/Erc20Token.vy:16 ERC1271.isValidSignature -> contracts/mock/MockBadERC1271.vy:11 (pure), contracts/mock/MockERC1271.vy:14 (pure)
- contracts/modules/Ownership.vy:9 UndyHq.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/registries/Switchboard.vy:37 TokenContract.setBlacklist -> contracts/modules/Erc20Token.vy:428 (nonpayable), contracts/vaults/modules/VaultErc20Token.vy:345 (nonpayable)
- contracts/registries/VaultRegistry.vy:28 EarnVault.withdrawFromYield -> contracts/core/userWallet/UserWallet.vy:298 (nonpayable), contracts/vaults/modules/EarnVaultWallet.vy:245 (nonpayable), contracts/vaults/modules/LevgVaultWallet.vy:284 (nonpayable)
- contracts/registries/VaultRegistry.vy:34 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/registries/WalletBackpack.vy:38 Sentinel.canSignerPerformActionWithConfig -> contracts/core/walletBackpack/Sentinel.vy:72 (view), contracts/mock/MockSentinel.vy:19 (view)
- contracts/registries/WalletBackpack.vy:39 Sentinel.checkManagerLimitsPostTx -> contracts/core/walletBackpack/Sentinel.vy:257 (view), contracts/mock/MockSentinel.vy:55 (view)
- contracts/registries/WalletBackpack.vy:40 Sentinel.isValidPayeeAndGetData -> contracts/core/walletBackpack/Sentinel.vy:448 (view), contracts/mock/MockSentinel.vy:37 (view)
- contracts/registries/WalletBackpack.vy:41 Sentinel.isValidChequeAndGetData -> contracts/core/walletBackpack/Sentinel.vy:651 (view), contracts/mock/MockSentinel.vy:78 (view)
- contracts/vaults/LevgVaultHelper.vy:13 LevgVault.convertToAssetsSafe -> contracts/vaults/EarnVault.vy:482 (view), contracts/vaults/LevgVault.vy:401 (view)
- contracts/vaults/LevgVaultHelper.vy:14 LevgVault.getTotalAssets -> contracts/vaults/EarnVault.vy:90 (view), contracts/vaults/LevgVault.vy:98 (view)
- contracts/vaults/LevgVaultHelper.vy:22 YieldLego.getUnderlyingAmountSafe -> contracts/legos/RipeLego.vy:293 (view), contracts/legos/UnderscoreLego.vy:186 (view), contracts/legos/yield/40Acres.vy:186 (view), contracts/legos/yield/AaveV3.vy:201 (view), contracts/legos/yield/Avantis.vy:183 (view), contracts/legos/yield/CompoundV3.vy:203 (view), contracts/legos/yield/Euler.vy:209 (view), contracts/legos/yield/ExtraFi.vy:196 (view), contracts/legos/yield/Fluid.vy:234 (view), contracts/legos/yield/Moonwell.vy:223 (view), contracts/legos/yield/Morpho.vy:231 (view), contracts/legos/yield/SkyPsm.vy:201 (view), contracts/legos/yield/Wasabi.vy:188 (view), contracts/mock/MockYieldLego.vy:142 (view)
- contracts/vaults/LevgVaultHelper.vy:23 YieldLego.getUnderlyingAmount -> contracts/legos/RipeLego.vy:278 (view), contracts/legos/UnderscoreLego.vy:171 (view), contracts/legos/yield/40Acres.vy:171 (view), contracts/legos/yield/AaveV3.vy:185 (view), contracts/legos/yield/Avantis.vy:168 (view), contracts/legos/yield/CompoundV3.vy:187 (view), contracts/legos/yield/Euler.vy:194 (view), contracts/legos/yield/ExtraFi.vy:178 (view), contracts/legos/yield/Fluid.vy:219 (view), contracts/legos/yield/Moonwell.vy:208 (view), contracts/legos/yield/Morpho.vy:216 (view), contracts/legos/yield/SkyPsm.vy:183 (view), contracts/legos/yield/Wasabi.vy:170 (view), contracts/mock/MockYieldLego.vy:120 (view)
- contracts/vaults/LevgVaultHelper.vy:24 YieldLego.canRegisterVaultToken -> contracts/legos/RipeLego.vy:464 (view), contracts/legos/UnderscoreLego.vy:357 (view), contracts/legos/yield/40Acres.vy:387 (view), contracts/legos/yield/AaveV3.vy:389 (view), contracts/legos/yield/Avantis.vy:383 (view), contracts/legos/yield/CompoundV3.vy:382 (view), contracts/legos/yield/Euler.vy:398 (view), contracts/legos/yield/ExtraFi.vy:397 (view), contracts/legos/yield/Fluid.vy:441 (view), contracts/legos/yield/Moonwell.vy:408 (view), contracts/legos/yield/Morpho.vy:487 (view), contracts/legos/yield/SkyPsm.vy:373 (view), contracts/legos/yield/Wasabi.vy:442 (view), contracts/mock/MockYieldLego.vy:318 (view)
- contracts/vaults/LevgVaultHelper.vy:36 RipeCreditEngine.getUserDebtAmount -> contracts/legos/RipeLego.vy:1018 (view), contracts/mock/MockRipe.vy:311 (view)
- contracts/vaults/LevgVaultHelper.vy:49 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/vaults/modules/EarnVaultWallet.vy:20 YieldLego.getUnderlyingBalances -> contracts/legos/RipeLego.vy:261 (view), contracts/legos/UnderscoreLego.vy:154 (view), contracts/legos/yield/40Acres.vy:154 (view), contracts/legos/yield/AaveV3.vy:176 (view), contracts/legos/yield/Avantis.vy:151 (view), contracts/legos/yield/CompoundV3.vy:178 (view), contracts/legos/yield/Euler.vy:177 (view), contracts/legos/yield/ExtraFi.vy:161 (view), contracts/legos/yield/Fluid.vy:202 (view), contracts/legos/yield/Moonwell.vy:191 (view), contracts/legos/yield/Morpho.vy:199 (view), contracts/legos/yield/SkyPsm.vy:166 (view), contracts/legos/yield/Wasabi.vy:153 (view), contracts/mock/MockYieldLego.vy:103 (view)
- contracts/vaults/modules/EarnVaultWallet.vy:21 YieldLego.getVaultTokenAmount -> contracts/legos/RipeLego.vy:397 (view), contracts/legos/UnderscoreLego.vy:290 (view), contracts/legos/yield/40Acres.vy:290 (view), contracts/legos/yield/AaveV3.vy:295 (view), contracts/legos/yield/Avantis.vy:287 (view), contracts/legos/yield/CompoundV3.vy:297 (view), contracts/legos/yield/Euler.vy:313 (view), contracts/legos/yield/ExtraFi.vy:303 (view), contracts/legos/yield/Fluid.vy:338 (view), contracts/legos/yield/Moonwell.vy:327 (view), contracts/legos/yield/Morpho.vy:335 (view), contracts/legos/yield/SkyPsm.vy:305 (view), contracts/legos/yield/Wasabi.vy:344 (view), contracts/mock/MockYieldLego.vy:253 (view)
- contracts/vaults/modules/EarnVaultWallet.vy:22 YieldLego.getUnderlyingAmount -> contracts/legos/RipeLego.vy:278 (view), contracts/legos/UnderscoreLego.vy:171 (view), contracts/legos/yield/40Acres.vy:171 (view), contracts/legos/yield/AaveV3.vy:185 (view), contracts/legos/yield/Avantis.vy:168 (view), contracts/legos/yield/CompoundV3.vy:187 (view), contracts/legos/yield/Euler.vy:194 (view), contracts/legos/yield/ExtraFi.vy:178 (view), contracts/legos/yield/Fluid.vy:219 (view), contracts/legos/yield/Moonwell.vy:208 (view), contracts/legos/yield/Morpho.vy:216 (view), contracts/legos/yield/SkyPsm.vy:183 (view), contracts/legos/yield/Wasabi.vy:170 (view), contracts/mock/MockYieldLego.vy:120 (view)
- contracts/vaults/modules/EarnVaultWallet.vy:23 YieldLego.getWithdrawalFees -> contracts/legos/RipeLego.vy:450 (view), contracts/legos/UnderscoreLego.vy:343 (view), contracts/legos/yield/40Acres.vy:373 (view), contracts/legos/yield/AaveV3.vy:375 (view), contracts/legos/yield/Avantis.vy:369 (view), contracts/legos/yield/CompoundV3.vy:368 (view), contracts/legos/yield/Euler.vy:384 (view), contracts/legos/yield/ExtraFi.vy:383 (view), contracts/legos/yield/Fluid.vy:427 (view), contracts/legos/yield/Moonwell.vy:394 (view), contracts/legos/yield/Morpho.vy:473 (view), contracts/legos/yield/SkyPsm.vy:359 (view), contracts/legos/yield/Wasabi.vy:428 (view), contracts/mock/MockYieldLego.vy:304 (view)
- contracts/vaults/modules/EarnVaultWallet.vy:32 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/vaults/modules/LevgVaultWallet.vy:32 YieldLego.getVaultTokenAmount -> contracts/legos/RipeLego.vy:397 (view), contracts/legos/UnderscoreLego.vy:290 (view), contracts/legos/yield/40Acres.vy:290 (view), contracts/legos/yield/AaveV3.vy:295 (view), contracts/legos/yield/Avantis.vy:287 (view), contracts/legos/yield/CompoundV3.vy:297 (view), contracts/legos/yield/Euler.vy:313 (view), contracts/legos/yield/ExtraFi.vy:303 (view), contracts/legos/yield/Fluid.vy:338 (view), contracts/legos/yield/Moonwell.vy:327 (view), contracts/legos/yield/Morpho.vy:335 (view), contracts/legos/yield/SkyPsm.vy:305 (view), contracts/legos/yield/Wasabi.vy:344 (view), contracts/mock/MockYieldLego.vy:253 (view)
- contracts/vaults/modules/LevgVaultWallet.vy:41 Registry.getAddr -> contracts/mock/MockRipe.vy:66 (view), contracts/modules/AddressRegistry.vy:524 (view)
- contracts/vaults/modules/VaultErc20Token.vy:15 ERC1271.isValidSignature -> contracts/mock/MockBadERC1271.vy:11 (pure), contracts/mock/MockERC1271.vy:14 (pure)
