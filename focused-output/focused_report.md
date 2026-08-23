# eFootball 11.0.1 focused UE4 static analysis
Sun Aug 23 13:55:07 UTC 2026

focus-work/libUE4.so: ELF 64-bit LSB shared object, ARM aarch64, version 1 (SYSV), dynamically linked, BuildID[md5/uuid]=f18d381f3b4e9aa1db097227b1fbb670, stripped
2ac4ff17ac8ad713d9531c2601e38a3c8335e02ea882ba2dc4445c191c1298cd  focus-work/libUE4.so

## Exact/high-precision networking strings
 9c8a8d dtls message too big
 9ef652 dtls1_hm_fragment_new
 a27ca2 dtls1_buffer_record
 a27cb6 dtls1_write_app_data_bytes
 a3a716 DTLSv1.2
 a4d7ec DTLS1 read hello verify request
 a60b14 dtls_construct_change_cipher_spec
 a60d12 DTLSv1
 a99f59 DTLS1 write hello verify request
 aad99b DTLSv0.9
 ae5fbe dtls1_check_timeout_num
 b0c8b4 do_dtls1_write
 b4582d dtls1_read_bytes
 b4583e dtls1_retransmit_message
 b6ae12 dtls1_process_record
 b7deec DTLSv1_listen
 ba5159 dtls1_process_buffered_records
 bb85d5 dtls1_read_failed
 bb85e7 dtls_process_hello_verify
 bc9e52 pesam.stun.service.konami.net
 bde5ea dtls_get_reassembled_message
 bf1719 dtls1_write_bytes
 c04711 DTLS_RECORD_LAYER_new
 c04727 dtls_wait_for_dry
 c17547 dtls1_preprocess_fragment
 c17561 dtls_construct_hello_verify_request

## Broader protocol strings
 9c6d22 Requested stun method. (CHANNEL_BIND_REQUEST)
 9c8a8d dtls message too big
 9da58a Requested stun method. (REFRESH_REQUEST)
 9ed683 Responded stun method. (ALLOCATE_SUCCESS_RESPONSE)
 9ed6b6 FINGERPRINT
 a26017 Responded unexpected stun method. (
 a2603b Responded stun method. (REFRESH_SUCCESS_RESPONSE)
 a388f4 ## Turn Status
 a97f6c MESSAGE_INTEGRITY
 aab94b ## Stun Status
 b8d21b Found pending candidate for reuse and CURLOPT_PIPEWAIT is set
 b8f459 MAPPED_ADDRESS
 bb6879 Responded stun method. (REFRESH_ERROR_RESPONSE)
 bb82be fingerprint size does not match digest
 bc9bae Responded stun method. (ALLOCATE_ERROR_RESPONSE)
 bc9e52 pesam.stun.service.konami.net
 bdc7d5 Responded stun method. (CHANNEL_BIND_ERROR_RESPONSE)
 bdc8a5 ## Stun Profile
 bef45a Requested stun method. (ALLOCATE_REQUEST)
 c02534 Responded stun method. (CHANNEL_BIND_SUCCESS_RESPONSE)

## Match state / score / clock strings
 11b739 glDrawArrays
 1229b6 glDrawBuffers
 122cde glDrawArraysInstanced
 122cf4 glDrawArraysIndirect
 122d09 glDrawElementsIndirect
 122d20 glDrawElementsInstanced
 122d38 glDrawElements
 20af45 _ZN5physx2Gu25PersistentContactManifold11drawPolygonERNS_2Cm12RenderOutputERKNS_6shdfnd3aos12PsTransformVEP13__Float32x4_tjj
 20afc2 _ZN5physx2Gu25PersistentContactManifold11drawPolygonERNS_2Cm12RenderOutputERKNS_6shdfnd3aos15PsMatTransformVEP13__Float32x4_tjj
 20b042 _ZN5physx2Gu25PersistentContactManifold12drawManifoldERKNS0_17PersistentContactERNS_2Cm12RenderOutputERKNS_6shdfnd3aos12PsTransformVESC_
 20b0cb _ZN5physx2Gu25PersistentContactManifold12drawManifoldERNS_2Cm12RenderOutputERKNS_6shdfnd3aos12PsTransformVES9_
 20b13a _ZN5physx2Gu25PersistentContactManifold12drawManifoldERNS_2Cm12RenderOutputERKNS_6shdfnd3aos12PsTransformVES9_RK13__Float32x2_t
 20b1ba _ZN5physx2Gu25PersistentContactManifold12drawTriangleERNS_2Cm12RenderOutputERK13__Float32x4_tS7_S7_j
 20b3ec _ZN5physx2Gu25PersistentContactManifold8drawLineERNS_2Cm12RenderOutputERK13__Float32x4_tS7_j
 20b449 _ZN5physx2Gu25PersistentContactManifold9drawPointERNS_2Cm12RenderOutputERK13__Float32x4_tfj
 20b4a5 _ZN5physx2Gu31SinglePersistentContactManifold12drawManifoldERNS_2Cm12RenderOutputERKNS_6shdfnd3aos12PsTransformVES9_
 20b85e _ZN5physx2Gu33MultiplePersistentContactManifold11drawPolygonERNS_2Cm12RenderOutputERKNS_6shdfnd3aos12PsTransformVEP13__Float32x4_tjj
 20b8e3 _ZN5physx2Gu33MultiplePersistentContactManifold12drawManifoldERNS_2Cm12RenderOutputERKNS_6shdfnd3aos12PsTransformVES9_
 20b95a _ZN5physx2Gu33MultiplePersistentContactManifold8drawLineERNS_2Cm12RenderOutputENS_6PxVec3ES5_j
 20b9b9 _ZN5physx2Gu33MultiplePersistentContactManifold8drawLineERNS_2Cm12RenderOutputERK13__Float32x4_tS7_j
 20ba1e _ZN5physx2Gu33MultiplePersistentContactManifold9drawPointERNS_2Cm12RenderOutputERK13__Float32x4_tfj
 9b9ddc Text_VictoryPoint_Value
 9baf85 EMatchFlowTask::HalftimeMenu
 9bb505 OnChangedDrawingTileViewItemDelegate__DelegateSignature
 9be8fd BeginDrawingViewport
 9c00fd K2_DrawLine
 9c0b8f DrawToRenderTargetContext
 9c557f drawopencloase_0_3_l
 9c8fa0 CheckMatchResult
 9cc504 EControlRigDrawHierarchyMode::Max
 9cd070 State_Draw
 9cd79c void UMenuTaskUserCompeTournamentDraw::CallbackFinishedShowNextMatchAnimation()
 9cd7ec -----------[%s] TargetDrawMatchInfo: RoundInfoIndex[%d]
 9cec41 FMenuEvCompeCompeEventMatchState::DRAWS
 9cef1f CallbackCloseRewardKeyView
 9cf238 OnRecieveCloseRequest
 9cf295 ETeamSelectStep::TEAM_SELECT_STEP_WAIT_DRAW_LINE
 9cf80f EMenuLeagueWinLoseDraw
 9d3f06 DrawDebugBox
 9d8e87 MenuGroupStageDrawBase
 9d906f CmdGetEventCompeGroupStageDraw
 9d92df round_match_result
 9d9b7d VICTORY
 9dcd36 SE_ENTER_AFTER_HALFTIME
 9dfa8b ControlRigDrawInstruction
 9e19c1 EMatchPhase::HalfTime
 9e1d48 DebugDrawGetKeyPads
 9e1f75 DrawingTileVIewItemInfo
 9e2977 DrawWidgetToRenderTexture
 9e36c1 IsHalfTime
 9e403b drawNumTitle
 9e4ae1 GetWithdrawnKonamiIdStr
 9e5574 DrawCalls
 9e5a16 VirtualTextureMainPassMaxDrawDistance
 9e743e DrawDebugTime
 9e7847 DrawTransform
 9e8c66 bDrawPolygonLabels
 9eb7b5 closeRate_DF_FW
 9eb7c5 closeRate_DF_FW_Retreat
 9eca7f league_match_result
 9f2fee ControlRigDrawContainer
 9f3006 EControlRigDrawHierarchyMode::Type
 9f414d Text_Draw_Value
 9f415d Text_Draw_Bonus
 9f54fa EDrawRatio::BP_DRAW_RATIO_16_9
 9f56a4 EndDrawWidgetToRenderTarget
 9f5bfe OnCloseRewardDialog
 9f6928 NeedDrawUserInfo
 9f96df DrawLine
 9f9eb5 EDrawDebugItemType::Sphere
 9f9ed0 EDrawDebugItemType::Type
 9fa2da DrawX
 9fa852 DrawDebugType
 9facc4 DrawDebugLine
 9fbc50 DrawCaptureRadius
 9fd38c js_run_3_2_000_guard_side_draw_sub_act095
 a02e6c KNOCKOUT_ROUND_TO_VICTORY
 a05cc9 DrawDirection
 a06282 RigUnit_DrawContainerSetThickness
 a06baa G:/PES22HC/Dev-600Series/UProject/PesMobile/Source/PesShared/Game/Menu/Common/GroupStageDraw/UCMenuGroupStageDrawBase.h
 a075c9 Online/EvCompe/EventCompe/MenuEvCompeEventCompeGroupStageDrawCanProceed
 a07611 Online/EvCompe/Tournament/MenuEvCompeWinner
 a082d2 DebugDrawStartTimeForGetPad
 a0866f GetDrawingWidtets
 a08e1d OnCloseRankingChangedAlertPopup
 a0b960 DebugDrawTrackedGeometry
 a0cf11 VMI_ShaderComplexityWithQuadOverdraw
 a0d2fa DrawMaterialTriangle
 a0eee7 bDrawFilledPolys
 a11c13 drawopencloase_0_3_r
 a125c4 Match/HalfTime/MatchHalfTimePost
 a12fb2 CMD_GET_EVENT_COMPE_GROUP_STAGE_DRAW
 a13246 SuspendedMatchResult
 a1964f DrawOpen
 a196d4 Text_Draw_Item
 a19d0f /Game/Assets/ui/Data/Widget/Mode/Event/GroupStageDraw/GroupStageDraw.GroupStageDraw_C
 a1a5e1 EDrawRatio::BP_DRAW_RATIO_NUM
 a1ac9e EGroupStageDrawCellType
 a1b80b EMenuLeagueWinLoseDraw::INVALID
 a1c574 EUserCompeLobbyResultType::LOBBY_RESULT_DEFEATED_GROUP
 a1d546 vkCmdDraw
 a1e819 GetDrawAtDesiredSize
 a1e849 bManuallyRedraw
 a1e859 RedrawTime
 a1e8e1 bDrawDebugLookAtTrackingPosition
 a1e902 bDrawDebugFocusPlane
 a1f91a DrawMaterialSimple
 a20382 bIsWinner
 a2372e draw::load::List::AnimationListCheck
 a2402c closeRate_MF_adjustX
 a25a2a skip_match_result
 a2aecc bDrawBones
 a2b031 bDrawDebug
 a31414 bDrawAtDesiredSize
 a32a33 EDrawDebugTrace::Persistent
 a32ec0 b3DDrawMode
 a33253 CachedMaxDrawDistance
 a33ec2 DefaultDrawDistance
 a34184 bDrawLabels
 a3755b FEINT_KIND_DRAWOPENCLOSE
 a38155 draw_rate
 a3dff5 RigUnit_DrawContainerGetInstruction
 a3fb46 Settings/Support/MenuWithdrawAgreement
 a40433 IsRedrawStep
 a40862 bDebugDrawInDesignTime
 a40aec CallbackPlayAnimeStep3ScorelessDraw
 a42301 EUserCompeLobbyResultType::LOBBY_RESULT_DEFEATED_ROUND
 a44248 CurrentDrawSize
 a44940 QueuedDrawDebugItem
 a44e12 AsyncLoadingUseFullTimeLimit
 a46703 OverrideDrawDistance
 a46bf6 bDrawPathCollidingGeometry
 a49579 adjustCloseRate_stratagy_defensive
 a4a3a7 FEINT_KIND_DRAWOPENCLOSE_L
 a4a455 HALFTIME
 a4b0be CmdGetEventCompeGroupStageDraw.php
 a51c68 /Game/Assets/ui/Data/Widget/Mode/Event/MatchMenuTournament/MatchMenuTournamentWinner.MatchMenuTournamentWinner_C
 a522fe Icon_Draw
 a53879 EGroupStageDrawCellType::User
 a544f7 NeedRedrawButtonIndexAry
 a580a1 DrawY
 a5b29a js_run_3_3_000_guard_side_set003_df_draw_act064
 a5db1e MenuMatchResultCoopStats
 a5dc96 isForRedraw
 a60f7c match_result_pk_match_start
 a611bc CheckMatchResultSameOnematchAndTotal
 a6acea DrawBox
 a6ad53 SetManuallyRedraw
 a6b3ee EDrawDebugItemType
 a6b86c DrawFrustum
 a6b889 bDrawShadow
 a6c0bc DrawDebugCamera
 a6d84d bDrawDefaultPolygonCost
 a6e0da feint_drawopen_0_3_f045
 a70638 drawopencloase_3_3_l
 a71876 AGENT_DRAW_WITHOUT_BIGTIME
 a71ec3 TaskEvCompeGetEventCompeGroupStageDraw
 a78950 PopupWithdrawFromCompeAlert
 a78d55 Match/Result/MatchResultCoopCommendationFromResult
 a7989a SetEvCompeMatchResult
 a79a5f DebugCheckDrawingItem
 a7b177 m_draws
 a7be6e DrawAs
 a7c757 ESlateBrushDrawType
 a7e1e0 DrawColor
 a7ed91 EDrawDebugTrace
 a7fcc9 NewInnerConeAngle
 a80167 bDrawSecondaryLines
 a8034c bDrawLabelsOnPathNodes
 a84183 MatchResultHalfTime
 a8a5d4 EControlRigDrawSettings::LineStrip
 a8aef9 /Game/Assets/ui/Data/Widget/TVGraphics/SwitchAssets_Original/CompeWinner/CompeWinner.CompeWinner_C
 a8c878 GetDrawRatioAnimationName
 a8f30c vkCmdDrawIndirect
 a9097d DrawText
 a909af bRedrawRequested
 a90ddb ShaderComplexityWithQuadOverdraw
 a91397 DrawXL
 a917d5 GlowInnerRadius
 a91cfd DrawDebugCapsule
 a9251c MinDrawDistance
 a94229 js_run_3_2_000_guard_side_draw_main_act068
 a95e78 match_to_match_result
 a972ae event_match_result
 a9752a MATCH_DRAW
 a9d9fb DrawContainer
 a9da78 EControlRigDrawSettings::Points
 a9fef3 DrawLinesWithGradient
 aa038c AnalystAdviceListOpenFrom::FROM_MATCH_RESULT
 aa1372 IsAnnounceGiveUpWinner
 aa3342 DebugDraw
 aa3e54 DrawSize
 aa4fd5 DrawRect
 aa5251 DrawDebugCylinder
 aa6277 bDrawDebugLagMarkers
 aa670e bDrawRadiusCircle
 aa694e bDrawFailedNavLinks
 ab14ca RigUnit_DrawContainerSetTransform
 ab2d13 /Game/Assets/ui/Data/Widget/General/MatchFlow/MatchResultCoop/MatchResultCoop.MatchResultCoop_C
 ab44d5 GetTaskBeforeMatchResult
 ab54ed EOnlineMultiplayMenuOrder::ONLINE_MULTIPLAY_MENU_HALFTIME
 ab643f ESlateBrushDrawType::Type
 ab6a85 bDrawEyeFirst
 ab71fb DrawTextFormatted
 ab76a9 QuadOverdraw
 ab81f3 DrawMaterial
 ab8577 DrawDebugPoint
 ab8586 DrawDebugString
 ab9d4a bDrawTriangleEdges
 aba5b0 feintrun_drawopen_3_3_f090
 abd4e4 kick_short_0_0_inside_y0_draw
 ac0833 gimmick_match_result
 ac1ac6 PxBinaryConverter: source meta data needs to match endianness with current system!
 ac320e ENiagaraRibbonDrawDirection
 ac483f CallbackCloseRewardView
 ac4c62 WithdrawFromCompe
 ac4ce8 void UMenuTaskUserCompeTournamentDraw::CallbackFinishedShowLineAnimation()
 ac5025 Match/Result/MatchResultCoopStatsFromHalfTime
 ac5088 Match/Result/MenuMatchResultUserList
 ac56f6 PatternImageUncompressedRawData
 ac604c AnalystAdviceListOpenFrom::FROM_HALFTIME
 ac9594 DrawSceneCommand_StartDelay
 ac96dd LDMaxDrawDistance
 acc436 CanvasForDrawMaterialToRenderTarget
 acd0fc feint_drawopen_0_3_f090
 ad04dc MatchResultTimeUpDemo
 ad0620 IsNeedRedrawForResult
 ad0636 Redraw
 ad087b ml_event_match_result
 ad0c19 is_withdrawn_konamiid
 ad396c CheckMatchResultDetail
 ad90b8 DrawWidgetToRenderTarget
 ada4fc SetAnnounceGiveUpWinner
 adaf71 m_isExtraTime
 adc44e EARFaceBlendShape::BrowInnerUp
 adcedd GetDrawSize
 adcf38 bDrawDebugTrackingFocusPoint
 add81f K2_DrawMaterialTriangle
 adde7c ReceiveDrawHUD
 adf44b bDrawIndicatorLines
 adf60a bDistinctlyDrawTilesBeingBuilt
 adfdef feintrun_drawdoubletouch_3_3_045_y0_sole_in_ver21
 adfe7f feint_drawdoubletouch_0_3_045_y0_sole_in_ver21
 ae087a js_run_3_3_000_guard_side_set003_of_draw_act068
 ae2c3b StatsTeamDraw
 ae6684 KIND_HALFTIME
 aea191 DrawOrder
 aeac47 Text_VictoryPoint_Item
 aebe67 EDrawRatio::BP_DRAW_RATIO_4_3
 af03d3 RequestRedraw
 af1c08 bSupported3DDrawMode
 af61ca FEINT_KIND_DRAWOPENCLOSE_R
 af6c8f ERR_TRANS_LINKED_WITHDRAWN_KONAMIID
 afdb24 CallbackPopupLowDrawQualityStadiumAlert
 afe255 Match/Result/MatchResultStrikeArenaCommendation
 afe948 EMatchFlowTask::HalftimeEnd
 aff3cc OnCloseRoomSettingView
 affa29 EMenuEvCompeMainMenuSelectKind::MatchResult
 b01aeb Paint/RecachedEmptyDrawLists
 b02b9d GetManuallyRedraw
 b03675 K2_DrawBorder
 b03683 K2_DrawPolygon
 b041c9 DrawDebugCircle
 b041d9 DrawDebugCone
 b041e7 DrawDebugFloatHistoryLocation
 b04205 DrawDebugPlane
 b085c7 closeRate_MF_adjustX_stratagy_defensive
 b099bb match_result_list
 b09bb7 HALF_TIME
 b0fd1f EControlRigDrawSettings::Primitive
 b10568 DrawingOffset
 b11691 Online/EvCompe/EventCompe/MenuEvCompeEventCompeGroupStageDrawCanReturn
 b14d5a vkCmdDrawIndexedIndirect
 b17775 BeginDrawCanvasToRenderTarget
 b18d41 bDrawClusters
 b1a79d feintrun_drawclose_3_3_000_y0_sole_in_act097
 b1b96f ExecDrawListener
 b1c6ab ADDED_TIME
 b1c810 MatchResultUserList
 b1ce6e EX_HALF_TIME
 b23066 bDrawLimits
 b24692 OnCloserAllocationAlert
 b254c4 IsDrawRatioWide
 b26921 EMenuLeagueWinLoseDraw::WIN
 b27444 EUserCompeLobbyResultType::LOBBY_RESULT_WINNER
 b2967e DrawLines
 b2a050 K2_DrawTriangle
 b2aa73 DrawDebugCoordinateSystem
 b2ab15 DrawLocation
 b2ab9d bDrawOnLevelStatusMap
 b3015f auto_match_result_list
 b35e1d EControlRigDrawSettings::DynamicMesh
 b365ca SpriteDrawCallRecord
 b36ca1 WinnerChoice
 b36e1d DrawClose
 b36e4c G:/PES22HC/Dev-600Series/UProject/PesMobile/Source/PesShared/Game/Menu/Match/Result/UCMenuMatchResultCoopCommendationBase.h
 b373bf ThirdPlaceMatch_Result_%s
 b385c9 DebugDrawTextTelopFastMode
 b39372 ClearEvCompeEventMatchResult
 b398ff GetDrawHeight
 b3c4eb bInDrawAtDesiredSize
 b3eefd EnableDebugDrawing
 b42b2f MenuEvCompeCompeEventGroupStageDraw
 b432ef get_match_result
 b48a46 RigUnit_DrawContainerSetColor
 b4aa9d GetDrawRatio
 b4ab11 DebugDrawTouchControlCondition
 b4b52f MenuChildCloseRequestEvents__DelegateSignature
 b4bd9b EMatchDemoType::MATCH_DEMO_TYPE_HALFTIME
 b4dc73 PrimitivesDrawn
 b4ef14 ServerDrawDebug
 b5138f DrawOffset
 b54b28 IsNeedRedrawForExpiredError
 b58434 NUM_MATCH_DRAW
 b5851e BGM_CALL_VICTORY
 b5b714 EControlRigDrawHierarchyMode
 b5b731 ControlRigDrawInterface
 b5cd40 PartsDetailRecord_Draw
 b5db54 DebugEnableDrawTileviewDelayTickList
 b5e656 drawScale
 b5fb00 drawNum
 b60a67 ESlateBrushDrawType::Border
 b61319 DrawScale
 b61a9f GetCurrentDrawSize
 b61ab2 SetDrawAtDesiredSize
 b6203a EDrawDebugItemType::OnScreenMessage
 b6244f K2_DrawBox
 b6245a DrawFont
 b62eac DrawDebugConeInDegrees
 b62ec3 DrawDebugFloatHistoryTransform
 b63007 MaxDrawDistance
 b6342e bUseMaxDrawCount
 b63dad SetDrawDebug
 b6432b bDrawDistanceToWall
 b6437e bDrawTileBounds
 b66f33 dfLineCloseRate
 b6e32e ENiagaraRibbonDrawDirection::FrontToBack
 b71e9f GetDrawWidth
 b7381d ESlateBrushDrawType::Box
 b74d9e EDrawDebugItemType::DirectionalArrow
 b74dc3 EDrawDebugItemType::CoordinateSystem
 b752ec PriorityAsyncLoadingExtraTime
 b754cb VMI_QuadOverdraw
 b75c57 bDebugDraw
 b75cf7 DrawDebugSphere
 b772b1 bDrawNavMeshEdges
 b78b7a feint_drawclose_0_3_000_y0_sole_in_act097
 b7b1df draw_spot_num
 b7e466 AddedTimeVariousData
 b7e5b3 NUM_DRAW
 b83232 void UMenuTaskUserCompeTournamentDraw::EndProgressAnimation()
 b83f16 DrawLineWithGradient
 b85323 EMenuLeagueWinLoseDraw::LOSE
 b88d88 PriorityLevelStreamingActorsUpdateExtraTime
 b8a8e6 bDrawMarkedForbiddenPolys
 b8c3c1 feint_drawclose_0_3_045_y0_sole_in_act097
 b8d3d4 DrawPlagin_SetCommunicateFlag
 b8e547 MatchResultHighlight
 b8eeba ml_event_match_result_list
 b91a32 AFTER_HALFTIME
 b94df5 EControlRigDrawSettings
 b96a13 Online/UserCompe/MenuUserCompeGroupStageDraw
 b992ac matchResultGetTimeTrophy
 b9a616 ESlateBrushDrawType::NoDrawType
 b9be94 K2_DrawTexture
 b9c7e3 DrawMaterialToRenderTarget
 b9d351 bDrawOnlyIfSelected
 b9db28 bDrawTileLabels
 ba0990 drawopencloase_3_3_r
 ba153a season_match_result
 ba897e ENiagaraRibbonDrawDirection::BackToFront
 ba8d5e EControlRigDrawHierarchyMode::Axes
 baa66d Match/Result/MatchResultCoopStatsFromResult
 baa782 Settings/LegalPrivacy/MenuPrivacyNoticeWithdrawalDetail
 baaeaf DebugForceDrawTouchRectangle
 baee64 GetRedrawTime
 baf53f EDrawDebugItemType::Line
 bb0068 DrawTextureSimple
 bb0325 EndDrawCanvasToRenderTarget
 bb03ac DrawDebugArrow
 bb13f8 bUseOverrideDrawDistance
 bb5ec6 AGENT_DRAW_WITHOUT_EPIC
 bb83f2 privilegeWithdrawn
 bbc484 DrawWorldOffset
 bbc53b DrawTransforms
 bbd4b8 G:/PES22HC/Dev-600Series/UProject/PesMobile/Source/PesShared/Game/Menu/Match/Result/UCMenuMatchResultCoopStatsCommendationBase.h
 bbe7dc DrawWidgetContext
 bbea7a bForceDebugDrawTouchPoint
 bbee33 OnCloseReturnCoinAlertPopup
 bbf83b ELobbyRoomReqest::CloseRequestedAlert
 bbff1f draws
 bc04d4 drawsTitleStr
 bc0b82 GraphDrawLineContainer
 bc1a40 DebugDrawPin
 bc2660 SetDrawSize
 bc266c InRedrawTime
 bc3a9c EDrawDebugTrace::ForOneFrame
 bc3ab9 EDrawDebugTrace::Type
 bc4f8a bEnableDrawing
 bc8f22 extra_match_result
 bcbd94 match_halftime
 bcbfb3 START_HALFTIME
 bd057f void UMenuTaskUserCompeTournamentDraw::CallbackFinishedShowEffectFinalAnimation()
 bd09ee Match/Result/MatchResultCoopStatsCommendationFromTimeUp
 bd1393 EDrawRatio
 bd1bad EGroupStageDrawCellType::Team
 bd3385 matchResultCompleteTrophy
 bd3985 EGameResult::GAMERESULT_DRAW
 bd6268 DrawYL
 bd6d31 LODDrawDistance
 bd80ae bDrawNavLinks
 bd80bc bDrawOctreeDetails
 bdbb7f UserCompeGroupStageDraw
 bdc183 AGENT_DRAW_WITHOUT_SHOWTIME
 be1d4a EControlRigDrawSettings::Lines
 be29e2 void UMenuTaskUserActionReport::CloseReportView()
 be343f bool UMenuTaskUserCompeTournamentDraw::UpdateDrawInfo(const UserCompeTournamentDrawInfo::MenuType)
 be3952 Match/Result/MatchResultStrikeArenaStatsCommendation
 be4abc MenuEvCompeTournamentEventWinnerData
 be6b41 DrawGraph
 be9503 bDrawAxis
 beaa68 bShouldDrawDebugData
 bec21b feintrun_drawclose_3_3_045_y0_sole_in_act097
 bed5ab sideCloseRate
 bee22b Match/HalfTime/MatchHalfTime
 bee715 draw_num
 beed65 MATCH_RESULT
 beef49 BOSS_MATCH_DRAW
 bf1abc match_halftime_demo
 bf524b bDrawPointsAsSpheres
 bf7651 CallbackPlayAnimeStep3Draw
 bf9203 m_isAdditionalSubstitutionExtraTime
 bf9c79 vkCmdDrawIndexed
 bfb023 SetRedrawTime
 bfc666 EDrawDebugTrace::ForDuration
 bfca93 MaxDrawCount
 bfd9f2 bDrawOctree
 bfdc04 StepToDebugDraw
 bfdd29 draw::load::List::Cleaner
 c002a1 DrawPlagin_SetLoadFlag
 c006ca DrawDemoObject
 c04589 Privilege Withdrawn
 c0985a bool UMenuTaskUserCompeTournamentDraw::SetMatchProgressDetailInfo(const UserCompeTournamentDrawOneMatchInfo &)
 c0a634 DebugDrawWindowState
 c0a6c1 BeginDrawWidgetToRenderTarget
 c0b920 EMenuLeagueWinLoseDraw::DRAW
 c0d5b3 ESlateBrushDrawType::Image
 c0e5d3 bUseManualRedraw
 c0f0ba K2_DrawMaterial
 c0f0ca K2_DrawText
 c0f843 DrawTexture
 c0fbdf EDrawDebugTrace::None
 c0fbf5 DrawDebugFrustum
 c0fc35 DrawTime
 c10e88 bDrawPolyEdges
 c111be bDrawFailedItems
 c11809 feintrun_drawopen_3_3_f045
 c1370e draw
 c14bf2 match_result
 c17ad0 CheckAddedTimeVariousData
 cfa41d drawing
 cfd3a8 Box_Drawing
 cfd3b4 Box_Drawing

## Focused symbols
    45: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND AInputEvent_getDeviceId
   350: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND glFramebufferTextureLayer
   628: 0000000008965dac   992 FUNC    GLOBAL DEFAULT   14 silk_encode_indices
   637: 00000000086d50dc   364 FUNC    GLOBAL DEFAULT   14 icu_64::SimpleLocaleKeyFactory::create(icu_64::ICUServiceKey const&, icu_64::ICUService const*, UErrorCode&) const
   645: 0000000008aacc2c   348 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_AttachDspTimeStretch
   724: 0000000008a44718    12 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_EnableBusSendOffsetWhenLevelNotExist
   833: 0000000008aca890   456 FUNC    GLOBAL DEFAULT   14 criAfxParagraphicEqualizer_Process
   873: 00000000089c57f8  1212 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::SetupAtomVoiceInternal(CriAtomVoiceConfigTag*, int, short)
   911: 00000000089c5644    44 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::CalculateNumSamplesPerPacket(float, float)
   938: 00000000088ccda4   696 FUNC    WEAK   DEFAULT   14 OT::hb_get_subtables_context_t::return_t OT::SubstLookupSubTable::dispatch<OT::hb_get_subtables_context_t>(OT::hb_get_subtables_context_t*, unsigned int) const
   950: 0000000008aec4a0    24 FUNC    GLOBAL DEFAULT   14 criFsDevice_SetThreadPriority
   997: 0000000008560a28    12 FUNC    GLOBAL DEFAULT   14 physx::Gu::RTreeTriangleMesh::getVerticesForModification()
  1079: 00000000088bc510   208 FUNC    WEAK   DEFAULT   14 OT::HintingDevice::get_x_delta(hb_font_t*) const
  1134: 000000000868b18c    36 FUNC    GLOBAL DEFAULT   14 icu_64::ICUBreakIteratorService::~ICUBreakIteratorService()
  1151: 0000000008aacb64   200 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_CalculateWorkSizeForDspTimeStretch
  1296: 00000000086d2088   384 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::get(icu_64::Locale const&, int, icu_64::Locale*, UErrorCode&) const
  1332: 00000000098943d8   392 OBJECT  GLOBAL DEFAULT   16 vtable for icu_64::ChoiceFormat
  1334: 0000000008a5d574   328 FUNC    GLOBAL DEFAULT   14 criAsrVoice_SetDspParameter
  1337: 00000000086cf5e0     8 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceKey::getID() const
  1374: 00000000088c1138   128 FUNC    WEAK   DEFAULT   14 OT::hb_would_apply_context_t::return_t OT::SingleSubst::dispatch<OT::hb_would_apply_context_t>(OT::hb_would_apply_context_t*) const
  1388: 00000000089c6b18    12 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice_Float32::SetCallbackGetFloat32PcmData(unsigned int (*)(void*, unsigned int, float**, unsigned int), void*)
  1392: 00000000086cf858    12 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceKey::getDynamicClassID() const
  1410: 00000000086d07c8   548 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::getVisibleIDs(icu_64::UVector&, icu_64::UnicodeString const*, UErrorCode&) const
  1448: 00000000087082c0   148 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::ChoiceFormat(icu_64::UnicodeString const&, UErrorCode&)
  1468: 0000000008a5c680   100 FUNC    GLOBAL DEFAULT   14 criAsrVoice_Execute
  1537: 00000000088cc9bc   396 FUNC    WEAK   DEFAULT   14 OT::hb_add_coverage_context_t<hb_set_digest_combiner_t<hb_set_digest_lowest_bits_t<unsigned long, 4u>, hb_set_digest_combiner_t<hb_set_digest_lowest_bits_t<unsigned long, 0u>, hb_set_digest_lowest_bits_t<unsigned long, 9u> > > >::return_t OT::SubstLookupSubTable::dispatch<OT::hb_add_coverage_context_t<hb_set_digest_combiner_t<hb_set_digest_lowest_bits_t<unsigned long, 4u>, hb_set_digest_combiner_t<hb_set_digest_lowest_bits_t<unsigned long, 0u>, hb_set_digest_lowest_bits_t<unsigned long, 9u> > > > >(OT::hb_add_coverage_context_t<hb_set_digest_combiner_t<hb_set_digest_lowest_bits_t<unsigned long, 4u>, hb_set_digest_combiner_t<hb_set_digest_lowest_bits_t<unsigned long, 0u>, hb_set_digest_lowest_bits_t<unsigned long, 9u> > > >*, unsigned int) const
  1625: 00000000088df4b4   340 FUNC    WEAK   DEFAULT   14 hb_sanitize_context_t::return_t AAT::KerxSubTable::dispatch<hb_sanitize_context_t>(hb_sanitize_context_t*) const
  1635: 0000000008a5d6bc   212 FUNC    GLOBAL DEFAULT   14 criAsrVoice_ResetDspParameters
  1669: 0000000008a6753c    44 FUNC    GLOBAL DEFAULT   14 criAtomVoice_IsAudioOutputActive
  1729: 00000000086cf73c   132 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceKey::parsePrefix(icu_64::UnicodeString&)
  1730: 00000000086d18d4   124 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::createKey(icu_64::UnicodeString const*, UErrorCode&) const
  1759: 0000000008a4fa3c    12 FUNC    GLOBAL DEFAULT   14 criAtomPlayer_SetMonitoringVoiceStopCallback
  1773: 00000000088db19c   592 FUNC    WEAK   DEFAULT   14 AAT::hb_aat_apply_context_t::return_t AAT::ChainSubtable<AAT::ExtendedTypes>::dispatch<AAT::hb_aat_apply_context_t>(AAT::hb_aat_apply_context_t*) const
  1793: 0000000008708400   184 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::ChoiceFormat(double const*, signed char const*, icu_64::UnicodeString const*, int)
  1903: 0000000008a68240    60 FUNC    GLOBAL DEFAULT   14 criAtomVoice_IsNcVoicePlaying
  1921: 00000000086d0b60    64 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::getDisplayName(icu_64::UnicodeString const&, icu_64::UnicodeString&) const
  1947: 0000000008613964    64 FUNC    GLOBAL DEFAULT   14 physx::PxVehicleGraph::updateTimeSlice(float const*)
  1977: 0000000008a5d830    76 FUNC    GLOBAL DEFAULT   14 criAsrVoice_SetSpatializer
  2059: 0000000008a67b04    20 FUNC    GLOBAL DEFAULT   14 criAtomVoice_Pause
  2087: 00000000087082c0   148 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::ChoiceFormat(icu_64::UnicodeString const&, UErrorCode&)
  2095: 0000000008a44020    24 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_GetAtomPlayer
  2264: 00000000086d27f8    96 FUNC    WEAK   DEFAULT   14 icu_64::ServiceEnumeration::reset(UErrorCode&)
  2348: 0000000008a58788     8 FUNC    GLOBAL DEFAULT   14 criAsrRack_SetOutputNcVoiceType
  2356: 00000000088c6f48   232 FUNC    WEAK   DEFAULT   14 OT::OffsetTo<OT::Device, OT::IntType<unsigned short, 2u>, true>::sanitize(hb_sanitize_context_t*, void const*) const
  2403: 0000000008709290   324 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::matchStringUntilLimitPart(icu_64::MessagePattern const&, int, int, icu_64::UnicodeString const&, int)
  2423: 0000000008290478    20 FUNC    GLOBAL DEFAULT   14 mixer_numvoices
  2457: 0000000008a43fd4    40 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_IsActive
  2533: 0000000008a69914   892 FUNC    GLOBAL DEFAULT   14 criNcVoice_ProcessInsertionDspAndInterleaveFloat32toInt16
  2548: 0000000000d085f9    35 OBJECT  GLOBAL DEFAULT   10 typeinfo name for icu_64::ICUBreakIteratorService
  2593: 0000000008a5c2b8   184 FUNC    GLOBAL DEFAULT   14 criAsrVoice_CalculateWorkSize
  2598: 0000000008af5df8    76 FUNC    GLOBAL DEFAULT   14 criFsReadDevice_IsCreatedDevice
  2620: 000000000870868c    64 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::~ChoiceFormat()
  2748: 00000000088ca88c   588 FUNC    WEAK   DEFAULT   14 hb_sanitize_context_t::return_t OT::Context::dispatch<hb_sanitize_context_t>(hb_sanitize_context_t*) const
  2795: 00000000086d1aa4     8 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::getTimestamp() const
  2821: 00000000089c6414    72 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::SetVolume(float)
  2932: 0000000009891200    24 OBJECT  GLOBAL DEFAULT   16 typeinfo for icu_64::ICUService
  2984: 00000000086d2308    20 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::registerInstance(icu_64::UObject*, icu_64::Locale const&, int, UErrorCode&)
  3002: 0000000008acaa70    28 FUNC    GLOBAL DEFAULT   14 criAfxParagraphicEqualizer_GetParameter
  3032: 0000000009895ae0    24 OBJECT  GLOBAL DEFAULT   16 typeinfo for icu_64::CalendarService
  3232: 00000000082e003c   104 FUNC    GLOBAL DEFAULT   14 physx::NpCloth::getSelfCollisionIndices(unsigned int*) const
  3267: 0000000008aebf18    92 FUNC    GLOBAL DEFAULT   14 criFsDevice_CalculateWorkSize
  3314: 0000000008a1d164    12 FUNC    GLOBAL DEFAULT   14 criStreamerManager_GetDefaultDeviceId
  3390: 0000000008a67a7c    20 FUNC    GLOBAL DEFAULT   14 criAtomVoice_SetSamplingRate
  3433: 0000000008aac9d8   212 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_CalculateWorkSizeForDspPitchShifter
  3439: 0000000008a6c5c8    24 FUNC    GLOBAL DEFAULT   14 criNcHcaMixer_RemoveVoice
  3514: 00000000086e1ac0   352 FUNC    GLOBAL DEFAULT   14 icu_64::UnifiedCache::_runEvictionSlice() const
  3548: 0000000008381e28     8 FUNC    WEAK   DEFAULT   14 physx::cloth::ClothImpl<physx::cloth::SwCloth>::getNumSelfCollisionIndices() const
  3608: 0000000008a5d4ac     8 FUNC    GLOBAL DEFAULT   14 criAsrVoice_SetContext
  3625: 0000000008998798    48 FUNC    GLOBAL DEFAULT   14 CriMvEasyPlayer::detachCenterVoice()
  3653: 0000000008ab9e24   152 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_CalculateWorkSizeForInstrumentVoicePool
  3714: 0000000008338b38   268 FUNC    GLOBAL DEFAULT   14 physx::Pt::SpatialHash::reorderParticleIndicesToPackets(unsigned int*, unsigned int, physx::Cm::BitMapBase<physx::shdfnd::NonTrackingAllocator> const&, unsigned short*)
  3718: 00000000083e141c    20 FUNC    GLOBAL DEFAULT   14 physx::Sc::SimulationController::udpateScBodyAndShapeSim(physx::PxsTransformCache&, physx::Bp::BoundsArray&, physx::PxBaseTask*)
  3775: 00000000088c1008   304 FUNC    WEAK   DEFAULT   14 OT::hb_would_apply_context_t::return_t OT::SubstLookupSubTable::dispatch<OT::hb_would_apply_context_t>(OT::hb_would_apply_context_t*, unsigned int) const
  3779: 0000000008ab2688     4 FUNC    GLOBAL DEFAULT   14 criAtomExAsr_PauseOutputVoice
  3845: 00000000089c53a4   120 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::Initialize()
  4059: 0000000008705510  1084 FUNC    GLOBAL DEFAULT   14 icu_64::MessagePattern::parseChoiceStyle(int, int, UParseError*, UErrorCode&)
  4086: 00000000089c6878   172 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::ResetBusSendLevel()
  4095: 00000000086cf864     4 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceFactory::~ICUServiceFactory()
  4138: 0000000008a44654   172 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_ForceResetBusSend
  4270: 00000000086d266c   168 FUNC    WEAK   DEFAULT   14 icu_64::ServiceEnumeration::clone() const
  4279: 0000000008a96af0    32 FUNC    GLOBAL DEFAULT   14 criatomexplayer_SetDeviceSendLevel
  4300: 0000000008a8d5c0   120 FUNC    GLOBAL DEFAULT   14 criAtomEx_GetNumUsedVirtualVoices
  4313: 00000000086d2030    68 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::~ICULocaleService()
  4316: 0000000008aebeac    92 FUNC    GLOBAL DEFAULT   14 criFsDecodeDevice_GetDecoder
  4320: 000000000853fe18  1448 FUNC    GLOBAL DEFAULT   14 physx::Gu::HeightField::parseTrianglesForCollisionVertices(unsigned short)
  4377: 00000000086d0008    20 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::getKey(icu_64::ICUServiceKey&, UErrorCode&) const
  4380: 00000000087234f8   680 FUNC    GLOBAL DEFAULT   14 icu_64::DateTimePatternGenerator::getFieldAndWidthIndices(char const*, UDateTimePGDisplayWidth*) const
  4412: 0000000008af64a8    24 FUNC    GLOBAL DEFAULT   14 criFsReadDevice_SetInitialThreadPriority
  4468: 0000000008aec484    12 FUNC    GLOBAL DEFAULT   14 criFsDevice_RequestToResume
  4507: 00000000088bcf0c   336 FUNC    WEAK   DEFAULT   14 OT::hb_collect_glyphs_context_t::return_t OT::SubstLookup::dispatch_recurse_func<OT::hb_collect_glyphs_context_t>(OT::hb_collect_glyphs_context_t*, unsigned int)
  4636: 0000000008a67bfc    64 FUNC    GLOBAL DEFAULT   14 criAtomVoice_IsDropped
  4640: 00000000088e18c0   492 FUNC    WEAK   DEFAULT   14 AAT::hb_aat_apply_context_t::return_t AAT::KerxSubTable::dispatch<AAT::hb_aat_apply_context_t>(AAT::hb_aat_apply_context_t*) const
  4681: 0000000008a53f48    16 FUNC    GLOBAL DEFAULT   14 criAtom_SetDeviceUpdateCallback
  4684: 0000000008a6a358    12 FUNC    GLOBAL DEFAULT   14 criNcVoiceAsr_GetInterface
  4755: 0000000008a75e10  9248 FUNC    GLOBAL DEFAULT   14 criAtomParameter2_CalcVoiceParameter
  4772: 00000000088b9430   232 FUNC    WEAK   DEFAULT   14 AAT::hb_aat_apply_context_t::return_t OT::KernSubTable<OT::KernOTSubTableHeader>::dispatch<AAT::hb_aat_apply_context_t>(AAT::hb_aat_apply_context_t*) const
  4795: 00000000087082b4    12 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::getDynamicClassID() const
  4839: 0000000008a8b3a4   264 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_AllocateHcaMxVoicePool
  4855: 0000000008752224   692 FUNC    GLOBAL DEFAULT   14 icu_64::ChineseCalendar::winterSolstice(int) const
  4871: 0000000008a47514    20 FUNC    GLOBAL DEFAULT   14 criAtomPlayerPool_SetVoiceEventCallback
  4872: 000000000824684c   168 FUNC    GLOBAL DEFAULT   14 std::__ndk1::random_device::random_device(std::__ndk1::basic_string<char, std::__ndk1::char_traits<char>, std::__ndk1::allocator<char> > const&)
  4925: 0000000008a5d8cc   100 FUNC    GLOBAL DEFAULT   14 criAsrVoice_ReturnPacket
  5115: 0000000008a5d4b4     8 FUNC    GLOBAL DEFAULT   14 criAsrVoice_GetContext
  5133: 0000000008a99b30   120 FUNC    GLOBAL DEFAULT   14 criAtomEx_EnumerateVoiceInfos
  5254: 0000000008a5c508   224 FUNC    GLOBAL DEFAULT   14 criAsrVoice_Destroy
  5312: 0000000008aac574   144 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_CalculateWorkSizeForDsp
  5317: 00000000089c8940    84 FUNC    GLOBAL DEFAULT   14 criManaStreamer_IsCandidate
  5333: 0000000008ac9fdc   152 FUNC    GLOBAL DEFAULT   14 criAfxParagraphicEqualizer_CalculateWorkSize
  5360: 0000000008708ddc    24 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::format(int, icu_64::UnicodeString&, icu_64::FieldPosition&) const
  5468: 000000000868b188     4 FUNC    GLOBAL DEFAULT   14 icu_64::ICUBreakIteratorService::~ICUBreakIteratorService()
  5482: 0000000008a50eb4     8 FUNC    GLOBAL DEFAULT   14 criAtomPlayer_SetDeviceSend
  5496: 00000000086d25fc    48 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::createKey(icu_64::UnicodeString const*, UErrorCode&) const
  5568: 00000000089c6968    40 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::GetAtomExPlaybackId()
  5576: 00000000088caad8   388 FUNC    WEAK   DEFAULT   14 hb_sanitize_context_t::return_t OT::ChainContext::dispatch<hb_sanitize_context_t>(hb_sanitize_context_t*) const
  5586: 0000000008af6350   332 FUNC    GLOBAL DEFAULT   14 criFsReadDevice_SetParameterToDeviceList
  5695: 00000000087084b8    92 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::ChoiceFormat(icu_64::ChoiceFormat const&)
  5738: 00000000084cb328   496 FUNC    GLOBAL DEFAULT   14 physx::MaterialIndicesStruct::getBinaryMetaData(physx::PxOutputStream&)
  5770: 0000000008a6795c   204 FUNC    GLOBAL DEFAULT   14 criAtomVoice_SetDefaultParameters
  6007: 000000000839c18c    56 FUNC    GLOBAL DEFAULT   14 physx::Sc::Scene::swapInteractionArrayIndices(unsigned int, unsigned int, physx::Sc::InteractionType::Enum)
  6008: 00000000086cf52c    68 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceKey::ICUServiceKey(icu_64::UnicodeString const&)
  6014: 0000000008a43efc   204 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_FreeVoice
  6024: 0000000008a6a140   364 FUNC    GLOBAL DEFAULT   14 criNcVoice_FlushInsertionDsp
  6175: 0000000008a68204    60 FUNC    GLOBAL DEFAULT   14 criAtomVoice_GetSpatializer
  6286: 0000000008a1d70c   232 FUNC    GLOBAL DEFAULT   14 criStreamerManager_DeleteStreamerByDeviceId
  6305: 0000000008aec490     8 FUNC    GLOBAL DEFAULT   14 criFsDevice_IsSuspended
  6392: 00000000086d2224   204 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::registerInstance(icu_64::UObject*, icu_64::UnicodeString const&, signed char, UErrorCode&)
  6425: 0000000008a43fc8    12 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_SetRawPcmMode
  6461: 0000000008aebf74   484 FUNC    GLOBAL DEFAULT   14 criFsDevice_CreateFromWork
  6481: 0000000008a553ec   132 FUNC    GLOBAL DEFAULT   14 criAtomAsr_PauseOutputVoice
  6514: 0000000008781be4   268 FUNC    GLOBAL DEFAULT   14 icu_64::CollationDataBuilder::setPrimaryRangeAndReturnNext(int, int, unsigned int, int, UErrorCode&)
  6522: 0000000008a5d87c     8 FUNC    GLOBAL DEFAULT   14 criAsrVoice_GetSpatializer
  6557: 0000000008aec6d0    88 FUNC    GLOBAL DEFAULT   14 criFsDispatcher_ReturnActionItem
  6660: 0000000008708db8    12 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::getFormats(int&) const
  6676: 00000000089c6578   100 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::SetPan(int, float)
  6721: 000000000a572700     8 OBJECT  GLOBAL DEFAULT   23 criatomvoice_hn_list
  6749: 00000000098911a0    24 OBJECT  GLOBAL DEFAULT   16 typeinfo for icu_64::ICUServiceFactory
  6790: 00000000089c5670   244 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::CriManaSoundAtomVoice()
  6923: 0000000008a5d494     8 FUNC    GLOBAL DEFAULT   14 criAsrVoice_GetNumRoutings
  6959: 0000000008708654    56 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::~ChoiceFormat()
  7049: 0000000008534a24     8 FUNC    WEAK   DEFAULT   14 physx::Gu::ConvexMesh::getNbVertices() const
  7071: 000000000855ffa8     8 FUNC    WEAK   DEFAULT   14 physx::Gu::TriangleMesh::getNbVertices() const
  7183: 0000000008a6a2f8     8 FUNC    GLOBAL DEFAULT   14 criNcvDummy_GetDeviceType
  7240: 000000000a57b1f8     8 OBJECT  GLOBAL DEFAULT   23 g_criatomex_monitoring_voice_stop_cb_obj
  7255: 00000000088bc458   184 FUNC    WEAK   DEFAULT   14 OT::Device::get_y_delta(hb_font_t*, OT::VariationStore const&) const
  7302: 0000000008aff160    16 FUNC    GLOBAL DEFAULT   14 MovieDecoder_EnableVoicePoolCreate
  7327: 0000000008a55e68   124 FUNC    GLOBAL DEFAULT   14 criAtomAsr_GetDeviceType
  7436: 0000000009891ce0   208 OBJECT  GLOBAL DEFAULT   16 vtable for icu_64::ICUNumberFormatService
  7506: 0000000008a42b48    32 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_GetFinalVoiceParameter
  7511: 0000000008386098    88 FUNC    GLOBAL DEFAULT   14 physx::cloth::ClothImpl<physx::cloth::SwCloth>::setSelfCollisionIndices(physx::cloth::Range<unsigned int const>)
  7654: 0000000008a5cf7c    28 FUNC    GLOBAL DEFAULT   14 criAsrVoice_IsStop
  7659: 0000000008a44498   104 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_GetMaxVoices
  7699: 00000000089c69c0     8 FUNC    WEAK   DEFAULT   14 CriManaSoundAtomVoice::~CriManaSoundAtomVoice()
  7771: 00000000089c633c   216 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::Pause(int)
  7817: 0000000008aec324    68 FUNC    GLOBAL DEFAULT   14 criFsDevice_AddTask
  7822: 00000000088ca278   228 FUNC    WEAK   DEFAULT   14 hb_sanitize_context_t::return_t OT::SubstLookupSubTable::dispatch<hb_sanitize_context_t>(hb_sanitize_context_t*, unsigned int) const
  7941: 0000000008a279b8   132 FUNC    GLOBAL DEFAULT   14 criAtomConfig_GetVoiceLimitGroupIndex
  7980: 0000000008af5d84    96 FUNC    GLOBAL DEFAULT   14 criFs_DetachIoDevice
  8019: 0000000008aac604   168 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_CalculateWorkSizeForDspAfx
  8205: 0000000009895a10   208 OBJECT  GLOBAL DEFAULT   16 vtable for icu_64::CalendarService
  8269: 00000000086d0028  1844 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::getKey(icu_64::ICUServiceKey&, icu_64::UnicodeString*, icu_64::ICUServiceFactory const*, UErrorCode&) const
  8286: 0000000008a5d4bc   120 FUNC    GLOBAL DEFAULT   14 criAsrVoice_SetDspActiveSwitch
  8315: 00000000089c5cb4   468 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::CleanupAtomVoiceInternal()
  8399: 0000000008a99a24    76 FUNC    GLOBAL DEFAULT   14 criAtomEx_SetVoiceEventCallback
  8424: 00000000086d4048     8 FUNC    GLOBAL DEFAULT   14 icu_64::LocaleKeyFactory::handleCreate(icu_64::Locale const&, int, icu_64::ICUService const*, UErrorCode&) const
  8440: 0000000008a6a2dc     8 FUNC    GLOBAL DEFAULT   14 criNcvDummy_GetOutputNcVoice
  8455: 00000000086cf864     4 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceFactory::~ICUServiceFactory()
  8488: 0000000008a67adc    12 FUNC    GLOBAL DEFAULT   14 criAtomVoice_Start
  8506: 0000000008a42a0c    68 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_SetMaxPitch
  8515: 00000000086def8c   192 FUNC    WEAK   DEFAULT   14 icu_64::ICUNumberFormatService::handleDefault(icu_64::ICUServiceKey const&, icu_64::UnicodeString*, UErrorCode&) const
  8533: 0000000008a75708  1296 FUNC    GLOBAL DEFAULT   14 criAtomParameter2_Calculate3dVoiceParameter
  8584: 0000000008a67c44    20 FUNC    GLOBAL DEFAULT   14 criAtomVoice_SetVolume
  8670: 00000000086d2030    68 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::~ICULocaleService()
  8695: 00000000083c0120     8 FUNC    GLOBAL DEFAULT   14 physx::PxsDefaultMemoryManager::createDeviceMemoryAllocator(unsigned int)
  8811: 000000000834e0b8   332 FUNC    WEAK   DEFAULT   14 physx::shdfnd::Array<void*, physx::shdfnd::InlineAllocator<512u, physx::shdfnd::ReflectionAllocator<physx::Sq::AABBTreeIndices> > >::growAndPushBack(void* const&)
  8884: 00000000088cbf70   124 FUNC    WEAK   DEFAULT   14 hb_sanitize_context_t::return_t OT::ExtensionFormat1<OT::ExtensionSubst>::dispatch<hb_sanitize_context_t>(hb_sanitize_context_t*) const
  8985: 0000000008705478   152 FUNC    GLOBAL DEFAULT   14 icu_64::MessagePattern::parseChoiceStyle(icu_64::UnicodeString const&, UParseError*, UErrorCode&)
  9024: 00000000089c64c0    60 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::ResetSendLevel()
  9052: 00000000086def7c    16 FUNC    WEAK   DEFAULT   14 icu_64::ICUNumberFormatService::cloneInstance(icu_64::UObject*) const
  9080: 0000000000d11e4e    22 OBJECT  GLOBAL DEFAULT   10 typeinfo name for icu_64::ICUService
  9119: 000000000834de90   220 FUNC    WEAK   DEFAULT   14 physx::shdfnd::internal::Stack<physx::shdfnd::ReflectionAllocator<physx::Sq::AABBTreeIndices> >::grow()
  9234: 00000000082900e0   100 FUNC    GLOBAL DEFAULT   14 mixer_getvoicepos
  9253: 00000000088bc5e0   208 FUNC    WEAK   DEFAULT   14 OT::HintingDevice::get_y_delta(hb_font_t*) const
  9342: 00000000089c62e8    84 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::Stop()
  9360: 0000000008a68e9c   236 FUNC    GLOBAL DEFAULT   14 criNcVoice_CalculateWorkSize
  9491: 0000000008af8474    12 FUNC    GLOBAL DEFAULT   14 criFsIo_GetDeviceId
  9504: 0000000008a5c370   408 FUNC    GLOBAL DEFAULT   14 criAsrVoice_Create
  9693: 00000000088ba5a0   440 FUNC    WEAK   DEFAULT   14 AAT::hb_aat_apply_context_t::return_t OT::KernSubTable<OT::KernAATSubTableHeader>::dispatch<AAT::hb_aat_apply_context_t>(AAT::hb_aat_apply_context_t*) const
  9696: 00000000088bd05c   428 FUNC    WEAK   DEFAULT   14 OT::hb_collect_glyphs_context_t::return_t OT::SubstLookupSubTable::dispatch<OT::hb_collect_glyphs_context_t>(OT::hb_collect_glyphs_context_t*, unsigned int) const
  9824: 000000000868b188     4 FUNC    GLOBAL DEFAULT   14 icu_64::ICUBreakIteratorService::~ICUBreakIteratorService()
  9932: 00000000088d208c   396 FUNC    WEAK   DEFAULT   14 OT::hb_add_coverage_context_t<hb_set_digest_combiner_t<hb_set_digest_lowest_bits_t<unsigned long, 4u>, hb_set_digest_combiner_t<hb_set_digest_lowest_bits_t<unsigned long, 0u>, hb_set_digest_lowest_bits_t<unsigned long, 9u> > > >::return_t OT::PosLookupSubTable::dispatch<OT::hb_add_coverage_context_t<hb_set_digest_combiner_t<hb_set_digest_lowest_bits_t<unsigned long, 4u>, hb_set_digest_combiner_t<hb_set_digest_lowest_bits_t<unsigned long, 0u>, hb_set_digest_lowest_bits_t<unsigned long, 9u> > > > >(OT::hb_add_coverage_context_t<hb_set_digest_combiner_t<hb_set_digest_lowest_bits_t<unsigned long, 4u>, hb_set_digest_combiner_t<hb_set_digest_lowest_bits_t<unsigned long, 0u>, hb_set_digest_lowest_bits_t<unsigned long, 9u> > > >*, unsigned int) const
 10004: 00000000084dd10c   456 FUNC    GLOBAL DEFAULT   14 physx::Gu::ReadIndices(unsigned short, unsigned int, unsigned short*, physx::PxInputStream&, bool)
 10106: 0000000008a9a094     4 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_SetServerFrequencyForWorkSizeCalculation
 10136: 0000000008a68140    72 FUNC    GLOBAL DEFAULT   14 criAtomVoice_SetDeviceSend
 10337: 00000000086d2414    60 FUNC    GLOBAL DEFAULT   14 icu_64::ServiceEnumeration::~ServiceEnumeration()
 10343: 0000000008a53f0c     8 FUNC    GLOBAL DEFAULT   14 criAtom_SetFreeTimeBufferingFlagForDefaultDevice
 10354: 0000000008a587a0     8 FUNC    GLOBAL DEFAULT   14 criAsrRack_GetVoice
 10361: 0000000008a34248    48 FUNC    GLOBAL DEFAULT   14 criAtomExAcb_GetDeviceSendLevelParametersInfoByCueName
 10401: 00000000089c5fd8    88 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::SetupUserPanning(unsigned int)
 10415: 0000000008a5d424    36 FUNC    GLOBAL DEFAULT   14 criAsrVoice_PutPacket
 10454: 00000000087351c4    56 FUNC    GLOBAL DEFAULT   14 icu_64::Calendar::registerFactory(icu_64::ICUServiceFactory*, UErrorCode&)
 10457: 0000000008a5d49c     8 FUNC    GLOBAL DEFAULT   14 criAsrVoice_GetOutputChannels
 10488: 0000000008a44038  1080 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_Execute
 10501: 00000000086d07b4     8 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::handleDefault(icu_64::ICUServiceKey const&, icu_64::UnicodeString*, UErrorCode&) const
 10510: 00000000089c64fc   124 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::SetSendLevel(int, CriAtomSpeakerIdTag, float)
 10595: 00000000086d07bc    12 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::getVisibleIDs(icu_64::UVector&, UErrorCode&) const
 10597: 0000000008a1da80    44 FUNC    GLOBAL DEFAULT   14 criStreamerManager_SetDefaultDeviceSpecForTools
 10621: 00000000099712a0    24 OBJECT  GLOBAL DEFAULT   23 m2tsd_relaysj
 10645: 000000000873e77c   304 FUNC    WEAK   DEFAULT   14 icu_64::CalendarService::CalendarService()
 10651: 00000000088d2218   716 FUNC    WEAK   DEFAULT   14 OT::hb_get_subtables_context_t::return_t OT::PosLookupSubTable::dispatch<OT::hb_get_subtables_context_t>(OT::hb_get_subtables_context_t*, unsigned int) const
 10710: 0000000008a5cf60    28 FUNC    GLOBAL DEFAULT   14 criAsrVoice_Pause
 10764: 0000000008ab9a7c   276 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_AllocateAiffVoicePool
 10823: 00000000086d2450    12 FUNC    GLOBAL DEFAULT   14 icu_64::ServiceEnumeration::getStaticClassID()
 10843: 00000000086d189c    32 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::isDefault() const
 10890: 0000000008a8af84   104 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_CalculateWorkSizeForHcaVoicePool
 10930: 00000000088cd180   408 FUNC    WEAK   DEFAULT   14 OT::hb_get_subtables_context_t::return_t OT::Context::dispatch<OT::hb_get_subtables_context_t>(OT::hb_get_subtables_context_t*) const
 10939: 000000000a5701b8     8 OBJECT  GLOBAL DEFAULT   23 CriManaSoundAtomVoice::s_cs_list
 11018: 0000000008acab80    20 FUNC    GLOBAL DEFAULT   14 criAfxParagraphicEqualizer_GetNumProcessChannels
 11113: 0000000008b14b48    12 FUNC    GLOBAL DEFAULT   14 criAdo_AudioOutSetOutputDeviceConfig
 11200: 00000000086d14e4   420 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::registerFactory(icu_64::ICUServiceFactory*, UErrorCode&)
 11284: 0000000008708654    56 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::~ChoiceFormat()
 11365: 00000000083cc248   464 FUNC    GLOBAL DEFAULT   14 physx::Dy::DynamicsContext::setDescFromIndices(physx::PxSolverConstraintDesc&, physx::PxsIndexedInteraction const&, unsigned int)
 11368: 000000000870909c   172 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::format(icu_64::Formattable const*, int, icu_64::UnicodeString&, icu_64::FieldPosition&, UErrorCode&) const
 11378: 0000000008a44700    12 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_EnableCalculationAisacControlFrom3dPosition
 11459: 0000000008a67f34     8 FUNC    GLOBAL DEFAULT   14 criAtomVoice_GetNcVoiceHandle
 11519: 00000000087351a0    36 FUNC    GLOBAL DEFAULT   14 icu_64::CalendarService::~CalendarService()
 11543: 000000000828aeec    52 FUNC    GLOBAL DEFAULT   14 virt_getvoicepos
 11595: 00000000086deca8    20 FUNC    WEAK   DEFAULT   14 icu_64::ICUNumberFormatFactory::handleCreate(icu_64::Locale const&, int, icu_64::ICUService const*, UErrorCode&) const
 11602: 0000000008a67c58     8 FUNC    GLOBAL DEFAULT   14 criAtomVoice_GetVolume
 11679: 0000000008a67f3c    56 FUNC    GLOBAL DEFAULT   14 criAtomVoice_SetInsertionDsp
 11690: 00000000086d231c   196 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::registerInstance(icu_64::UObject*, icu_64::Locale const&, int, int, UErrorCode&)
 11739: 0000000008a6970c   520 FUNC    GLOBAL DEFAULT   14 criNcVoice_DownmixData
 11766: 00000000089ee6a0    84 FUNC    GLOBAL DEFAULT   14 vpx_codec_register_put_slice_cb
 11836: 0000000008a68f88   208 FUNC    GLOBAL DEFAULT   14 criNcVoice_Create
 11837: 0000000008af6034   180 FUNC    GLOBAL DEFAULT   14 criFsReadDevice_RequestToResumeAll
 11872: 00000000089c69ac    20 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::UnSetCategory()
 11878: 00000000088bfe88  1752 FUNC    WEAK   DEFAULT   14 OT::hb_collect_glyphs_context_t::return_t OT::PosLookupSubTable::dispatch<OT::hb_collect_glyphs_context_t>(OT::hb_collect_glyphs_context_t*, unsigned int) const
 11903: 0000000008a3dc7c    72 FUNC    GLOBAL DEFAULT   14 criAtomTblVoiceLimitGroupWork_Initialize
 11965: 000000000868b734   188 FUNC    WEAK   DEFAULT   14 icu_64::ICUBreakIteratorService::handleDefault(icu_64::ICUServiceKey const&, icu_64::UnicodeString*, UErrorCode&) const
 12062: 00000000086cfbfc    12 FUNC    GLOBAL DEFAULT   14 icu_64::ServiceListener::getStaticClassID()
 12077: 0000000008a44564   128 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_StopAwbPlayback
 12111: 00000000085405a0   300 FUNC    GLOBAL DEFAULT   14 physx::getEdgeTriangleIndices(physx::Gu::HeightField const&, physx::EdgeData const&, unsigned int*)
 12133: 0000000008af60e8   384 FUNC    GLOBAL DEFAULT   14 criFsReadDevice_IsSuspendedAll
 12138: 0000000008a5d48c     8 FUNC    GLOBAL DEFAULT   14 criAsrVoice_ResetRouting
 12239: 00000000089c5e88   336 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::SetupAutoPanning(unsigned int)
 12257: 0000000000d14c2f    27 OBJECT  GLOBAL DEFAULT   10 typeinfo name for icu_64::CalendarService
 12283: 000000000868b708    28 FUNC    WEAK   DEFAULT   14 icu_64::ICUBreakIteratorService::isDefault() const
 12296: 00000000089c6b24     4 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice_Float32::SetCallbackGetSint16PcmData(unsigned int (*)(void*, unsigned int, short**, unsigned int), void*)
 12367: 0000000000d11e18    29 OBJECT  GLOBAL DEFAULT   10 typeinfo name for icu_64::ICUServiceFactory
 12368: 0000000008a99c28    72 FUNC    GLOBAL DEFAULT   14 criAtomEx_SetMonitoringVoiceStopCallback
 12404: 00000000089c6b0c     4 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice_Float32::DestroyOutput()
 12405: 0000000008af6268   228 FUNC    GLOBAL DEFAULT   14 criFsReadDevice_IsSuspendedAny
 12475: 0000000008af649c    12 FUNC    GLOBAL DEFAULT   14 criFsReadDevice_SetInitialThreadStackSize
 12478: 0000000008a68014    48 FUNC    GLOBAL DEFAULT   14 criAtomVoice_ResetDspParameters
 12495: 0000000008a67d20   100 FUNC    GLOBAL DEFAULT   14 criAtomVoice_ResetPan
 12506: 0000000008aac924   180 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_DetachDsp
 12559: 0000000009891388   104 OBJECT  GLOBAL DEFAULT   16 vtable for icu_64::ServiceEnumeration
 12645: 00000000089c6990     8 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::SetAmbisonicsConfig(CriManaSound::AmbisonicsConfig)
 12683: 000000000a570230     4 OBJECT  GLOBAL DEFAULT   23 CriManaSoundAtomEx::available_voice_pool_id_for_mana_sound
 12732: 0000000008ab6178     4 FUNC    GLOBAL DEFAULT   14 criAtomExAsrRack_GetDeviceType
 12758: 0000000008a58768     8 FUNC    GLOBAL DEFAULT   14 criAsrRack_AddAsrVoice
 12805: 00000000087575e4    16 FUNC    WEAK   DEFAULT   14 icu_64::ICUCollatorService::cloneInstance(icu_64::UObject*) const
 12806: 0000000008a445e4    68 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_IsPathPointerRefered
 12817: 0000000008aac6ac   172 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_AttachDspAfx
 12830: 0000000008a6338c     8 FUNC    GLOBAL DEFAULT   14 criNcMic_GetNumDevices
 12844: 00000000086cf6b4   128 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceKey::isFallbackOf(icu_64::UnicodeString const&) const
 12881: 00000000089c6b28   496 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice_Float32::SubmitOnePacket()
 13087: 0000000008a949d8    40 FUNC    GLOBAL DEFAULT   14 criAtomExPlayer_SetVoiceControlMethod
 13099: 0000000008b188a0    16 FUNC    GLOBAL DEFAULT   14 criVsd_SetAudioOutputDeviceConfig
 13127: 0000000008a67d84   100 FUNC    GLOBAL DEFAULT   14 criAtomVoice_ResetSendLevel
 13179: 0000000008a68af4   208 FUNC    GLOBAL DEFAULT   14 criNcVoice_Initialize
 13223: 00000000086d245c    12 FUNC    GLOBAL DEFAULT   14 icu_64::ServiceEnumeration::getDynamicClassID() const
 13233: 0000000008a42884   272 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_Initialize
 13283: 00000000089bf568   732 FUNC    GLOBAL DEFAULT   14 MPVSL_DecSliceOne
 13365: 0000000008a597a0     8 FUNC    GLOBAL DEFAULT   14 criAsr_RemoveVoice
 13384: 0000000008af5ecc   180 FUNC    GLOBAL DEFAULT   14 criFsReadDevice_ExecuteServer
 13391: 0000000008a6deb0   136 FUNC    GLOBAL DEFAULT   14 criAtomInstrumentVoice_Initialize
 13521: 00000000089c6a80   140 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice_Float32::CreateOutput(_criheap_struct*, unsigned int, unsigned int)
 13526: 0000000008708f88   276 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::findSubMessage(icu_64::MessagePattern const&, int, double)
 13550: 0000000008a6a2e8     4 FUNC    GLOBAL DEFAULT   14 criNcvDummy_SetDeviceSend
 13593: 0000000008a1d5f0   284 FUNC    GLOBAL DEFAULT   14 criStreamerManager_AddStreamerByDeviceId
 13601: 0000000008708354   172 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::ChoiceFormat(double const*, icu_64::UnicodeString const*, int)
 13691: 0000000008a8ac2c   280 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_AllocateRawPcmVoicePool
 13728: 0000000008a3dcc4    88 FUNC    GLOBAL DEFAULT   14 criAtomTblVoiceLimitGroupWork_GetItem
 13741: 0000000008aebf14     4 FUNC    GLOBAL DEFAULT   14 criFsDecodeDevice_AddTask
 13833: 000000000a57b1f0     8 OBJECT  GLOBAL DEFAULT   23 g_criatomex_monitoring_voice_stop_cb_func
 13945: 0000000008a68a28    16 FUNC    GLOBAL DEFAULT   14 criNcVoice_RegisterInterface
 13989: 0000000008a5d898     8 FUNC    GLOBAL DEFAULT   14 criAsrVoice_SetInputCallback
 14018: 00000000087088e0    48 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::applyPattern(icu_64::UnicodeString const&, UParseError&, UErrorCode&)
 14143: 00000000088ca604   324 FUNC    WEAK   DEFAULT   14 hb_sanitize_context_t::return_t OT::AlternateSubst::dispatch<hb_sanitize_context_t>(hb_sanitize_context_t*) const
 14234: 0000000008acaa58    24 FUNC    GLOBAL DEFAULT   14 criAfxParagraphicEqualizer_SetParameter
 14284: 00000000084dd014   248 FUNC    GLOBAL DEFAULT   14 physx::Gu::StoreIndices(unsigned short, unsigned int, unsigned short const*, physx::PxOutputStream&, bool)
 14288: 00000000089951e4    92 FUNC    GLOBAL DEFAULT   14 CriMvEasyPlayer::isAvailableCenterVoice(CriMvStreamingParameters const*)
 14300: 0000000008246918   148 FUNC    GLOBAL DEFAULT   14 std::__ndk1::random_device::operator()()
 14393: 00000000088ca748   324 FUNC    WEAK   DEFAULT   14 hb_sanitize_context_t::return_t OT::LigatureSubst::dispatch<hb_sanitize_context_t>(hb_sanitize_context_t*) const
 14413: 0000000008984e04  1480 FUNC    GLOBAL DEFAULT   14 swappy::SwappyCommon::isDeviceUnsupported()
 14467: 0000000008adb568    72 FUNC    GLOBAL DEFAULT   14 criFs_SetReadDeviceEnabled
 14516: 00000000086d11dc    12 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::getDisplayNames(icu_64::UVector&, icu_64::Locale const&, UErrorCode&) const
 14579: 0000000008a67a90    76 FUNC    GLOBAL DEFAULT   14 criAtomVoice_Setup
 14592: 00000000086d23e0    52 FUNC    GLOBAL DEFAULT   14 icu_64::ServiceEnumeration::~ServiceEnumeration()
 14598: 0000000008a427f0   148 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_CalculateWorkSize
 14665: 0000000008a67bbc    64 FUNC    GLOBAL DEFAULT   14 criAtomVoice_GetNumBufferedSamples
 14763: 0000000009891148    24 OBJECT  GLOBAL DEFAULT   16 typeinfo for icu_64::ICUServiceKey
 14823: 00000000086cf7c0   140 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceKey::parseSuffix(icu_64::UnicodeString&)
 14855: 0000000008aebdf0   160 FUNC    GLOBAL DEFAULT   14 criFsDecodeDevice_Finalize
 14857: 0000000008b14b08     8 FUNC    GLOBAL DEFAULT   14 criAdo_EnableVoicePoolCreate
 14858: 000000000828a938   160 FUNC    GLOBAL DEFAULT   14 virt_resetvoice
 14862: 0000000008a4fa20    28 FUNC    GLOBAL DEFAULT   14 criAtomPlayer_SetMonitoringStopVoicePlaybackId
 14971: 0000000008a8a3ec   104 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_CalculateWorkSizeForAdxVoicePool
 15053: 00000000089c6034   108 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::GetStatus()
 15122: 000000000873e670   200 FUNC    WEAK   DEFAULT   14 icu_64::CalendarService::handleDefault(icu_64::ICUServiceKey const&, icu_64::UnicodeString*, UErrorCode&) const
 15232: 00000000086df0b0   324 FUNC    WEAK   DEFAULT   14 icu_64::ICUNumberFormatService::ICUNumberFormatService()
 15336: 00000000086cfdbc   100 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::ICUService(icu_64::UnicodeString const&)
 15561: 00000000086d18bc    24 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::countFactories() const
 15575: 0000000009891db0    24 OBJECT  GLOBAL DEFAULT   16 typeinfo for icu_64::ICUNumberFormatService
 15597: 0000000008a6c910     8 FUNC    GLOBAL DEFAULT   14 criNcHcaMixer_GetOutputNcVoice
 15687: 0000000008a55cf4   104 FUNC    GLOBAL DEFAULT   14 criAtomAsr_GetOutputNcVoice
 15707: 0000000008a42a50   248 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_SetGroupInfo
 15777: 000000000873519c     4 FUNC    GLOBAL DEFAULT   14 icu_64::CalendarService::~CalendarService()
 15782: 00000000086d19ec    64 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::clearServiceCache()
 15869: 0000000009894560    24 OBJECT  GLOBAL DEFAULT   16 typeinfo for icu_64::ChoiceFormat
 15874: 00000000082dffd8    96 FUNC    GLOBAL DEFAULT   14 physx::NpCloth::setSelfCollisionIndices(unsigned int const*, unsigned int)
 15898: 00000000089c6998    20 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::SetCategoryByName(char const*)
 16013: 0000000008543f1c   352 FUNC    WEAK   DEFAULT   14 physx::Gu::HeightField::getTriangleAdjacencyIndices(unsigned int, unsigned int, unsigned int, unsigned int, unsigned int&, unsigned int&, unsigned int&) const
 16050: 000000000829001c   196 FUNC    GLOBAL DEFAULT   14 mixer_voicepos
 16097: 0000000009890fe8    96 OBJECT  GLOBAL DEFAULT   16 vtable for icu_64::ICUServiceKey
 16116: 0000000008a69c90   676 FUNC    GLOBAL DEFAULT   14 criNcVoice_FlushInsertionDspAndInterleaveFloat32toInt16
 16137: 00000000086dd8e4    36 FUNC    GLOBAL DEFAULT   14 icu_64::ICUNumberFormatService::~ICUNumberFormatService()
 16147: 00000000086cff90   120 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::get(icu_64::UnicodeString const&, icu_64::UnicodeString*, UErrorCode&) const
 16175: 00000000086d1a2c    52 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::acceptsListener(icu_64::EventListener const&) const
 16196: 00000000089c541c   428 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::ExecuteServer(void*)
 16278: 000000000996a014     4 OBJECT  GLOBAL DEFAULT   22 g_criatomex_monitoring_voice_stop_playback_id
 16280: 0000000008755a6c   188 FUNC    GLOBAL DEFAULT   14 icu_64::ICUCollatorFactory::create(icu_64::ICUServiceKey const&, icu_64::ICUService const*, UErrorCode&) const
 16281: 00000000088dd400   656 FUNC    WEAK   DEFAULT   14 AAT::hb_aat_apply_context_t::return_t AAT::ChainSubtable<AAT::ObsoleteTypes>::dispatch<AAT::hb_aat_apply_context_t>(AAT::hb_aat_apply_context_t*) const
 16292: 0000000008708dc4    24 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::format(long, icu_64::UnicodeString&, icu_64::FieldPosition&) const
 16326: 0000000008a7b6a4    16 FUNC    GLOBAL DEFAULT   14 criAtomParameter2_HasDeviceSendLevel
 16358: 0000000008a5cda4     8 FUNC    GLOBAL DEFAULT   14 criAsrVoice_GetInputChannels
 16361: 0000000008a66e08   164 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_CalculateWorkSizeForSpatializer
 16438: 00000000086cfd64    88 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::ICUService()
 16483: 00000000089c65dc    28 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::GetPan(int)
 16536: 0000000008af6718    76 FUNC    GLOBAL DEFAULT   14 criFs_CalculateWorkSizeForAttachIoDevice
 16574: 0000000008a1da6c    20 FUNC    GLOBAL DEFAULT   14 criStreamerManager_GetDefaultConfigByDeviceId
 16602: 0000000008709148    48 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::parse(icu_64::UnicodeString const&, icu_64::Formattable&, icu_64::ParsePosition&) const
 16696: 00000000083e59dc    16 FUNC    GLOBAL DEFAULT   14 physx::Sc::ClothCore::getNbSelfCollisionIndices() const
 16754: 0000000008707214   428 FUNC    GLOBAL DEFAULT   14 icu_64::MessagePattern::isChoice(int)
 16764: 00000000088c224c   428 FUNC    WEAK   DEFAULT   14 OT::hb_closure_context_t::return_t OT::SubstLookupSubTable::dispatch<OT::hb_closure_context_t>(OT::hb_closure_context_t*, unsigned int) const
 16784: 0000000008a59798     8 FUNC    GLOBAL DEFAULT   14 criAsr_AddVoice
 16821: 0000000008a67ae8    28 FUNC    GLOBAL DEFAULT   14 criAtomVoice_Stop
 16828: 0000000008a5d008    20 FUNC    GLOBAL DEFAULT   14 criAsrVoice_SetSamplingRate
 16917: 0000000008708400   184 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::ChoiceFormat(double const*, signed char const*, icu_64::UnicodeString const*, int)
 17074: 0000000008a5d01c     8 FUNC    GLOBAL DEFAULT   14 criAsrVoice_GetSamplingRate
 17113: 0000000008a5cdb8   352 FUNC    GLOBAL DEFAULT   14 criAsrVoice_Start
 17181: 00000000083dc374    48 FUNC    GLOBAL DEFAULT   14 physx::Sc::ShapeCore::getNbMaterialIndices() const
 17224: 00000000088cd318   368 FUNC    WEAK   DEFAULT   14 OT::hb_get_subtables_context_t::return_t OT::ChainContext::dispatch<OT::hb_get_subtables_context_t>(OT::hb_get_subtables_context_t*) const
 17377: 00000000086cff1c     4 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::~ICUService()
 17569: 0000000008a67638   804 FUNC    GLOBAL DEFAULT   14 criAtomVoice_Create
 17582: 0000000008a8afec   276 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_AllocateHcaVoicePool
 17591: 00000000083dc17c   356 FUNC    GLOBAL DEFAULT   14 physx::Sc::ShapeCore::setMaterialIndices(unsigned short const*, unsigned short)
 17626: 00000000086d0e1c   960 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::getDisplayNames(icu_64::UVector&, icu_64::Locale const&, icu_64::UnicodeString const*, UErrorCode&) const
 17813: 0000000008a99fd0    36 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_FreeAll
 17891: 00000000088cd05c   292 FUNC    WEAK   DEFAULT   14 OT::hb_get_subtables_context_t::return_t OT::SingleSubst::dispatch<OT::hb_get_subtables_context_t>(OT::hb_get_subtables_context_t*) const
 17907: 0000000008757904   352 FUNC    WEAK   DEFAULT   14 icu_64::ICUCollatorService::ICUCollatorService()
 17914: 0000000008a5d930   228 FUNC    GLOBAL DEFAULT   14 criAsrVoiceList_AddVoice
 17984: 00000000089c5764   144 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::SetupVoiceConfig(CriAtomVoiceConfigTag*, unsigned int, unsigned int, unsigned int)
 18036: 000000000874d8e0    12 FUNC    GLOBAL DEFAULT   14 icu_64::CalendarAstronomer::SUMMER_SOLSTICE()
 18097: 0000000008708910    16 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::toPattern(icu_64::UnicodeString&) const
 18270: 0000000008706f4c    48 FUNC    GLOBAL DEFAULT   14 icu_64::MessagePattern::inTopLevelChoiceMessage(int, UMessagePatternArgType)
 18271: 00000000087575f4   236 FUNC    WEAK   DEFAULT   14 icu_64::ICUCollatorService::handleDefault(icu_64::ICUServiceKey const&, icu_64::UnicodeString*, UErrorCode&) const
 18279: 0000000008a68188    56 FUNC    GLOBAL DEFAULT   14 criAtomVoice_SetVirtualSurroundFrontBypassFlag
 18288: 0000000008a67c94   140 FUNC    GLOBAL DEFAULT   14 criAtomVoice_SetPan
 18388: 0000000008a42b74  1568 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_AllocateVoice
 18437: 000000000874d8ec    12 FUNC    GLOBAL DEFAULT   14 icu_64::CalendarAstronomer::WINTER_SOLSTICE()
 18503: 00000000086d169c   292 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::unregister(void const*, UErrorCode&)
 18515: 00000000089c6474    76 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::SetPitch(int, int)
 18518: 0000000008388b5c    12 FUNC    GLOBAL DEFAULT   14 physx::cloth::SwFabric::getNumIndices() const
 18524: 0000000008388b68    12 FUNC    GLOBAL DEFAULT   14 non-virtual thunk to physx::cloth::SwFabric::getNumIndices() const
 18534: 00000000089c60a0   216 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::GetTime(unsigned long long&, unsigned long long&)
 18588: 00000000089c57f4     4 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::SetupAtomVoice(CriAtomVoiceConfigTag*, int, short)
 18647: 00000000086d1fc4   108 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::ICULocaleService(icu_64::UnicodeString const&)
 18666: 00000000086cfbf8     4 FUNC    GLOBAL DEFAULT   14 icu_64::ServiceListener::~ServiceListener()
 18792: 0000000008755bc0    36 FUNC    GLOBAL DEFAULT   14 icu_64::ICUCollatorService::~ICUCollatorService()
 18806: 0000000008af5de4    12 FUNC    GLOBAL DEFAULT   14 criFsReadDevice_IsInitialized
 18838: 0000000008af634c     4 FUNC    GLOBAL DEFAULT   14 criFsReadDevice_AddTask
 18876: 0000000008a68c1c   320 FUNC    GLOBAL DEFAULT   14 criNcVoice_Begin
 18911: 00000000083efb40     8 FUNC    GLOBAL DEFAULT   14 physx::Sc::ParticleSystemCore::returnStandaloneData(physx::Pt::ParticleData*)
 18946: 00000000086d23e0    52 FUNC    GLOBAL DEFAULT   14 icu_64::ServiceEnumeration::~ServiceEnumeration()
 18959: 0000000008708dac    12 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::getClosures(int&) const
 19002: 0000000008a69f34   524 FUNC    GLOBAL DEFAULT   14 criNcVoice_ProcessInsertionDsp
 19067: 00000000083cc418   332 FUNC    GLOBAL DEFAULT   14 physx::Dy::DynamicsContext::setDescFromIndices(physx::PxSolverConstraintDesc&, unsigned int, physx::IG::SimpleIslandManager const&, unsigned int*, unsigned int)
 19114: 0000000008a5da14   204 FUNC    GLOBAL DEFAULT   14 criAsrVoiceList_RemoveAllVoices
 19115: 0000000008a67f74    72 FUNC    GLOBAL DEFAULT   14 criAtomVoice_SetDspActiveSwitch
 19191: 0000000008a93fdc    12 FUNC    GLOBAL DEFAULT   14 criAtomExPlayer_EnableAdjustDeviceBuffer
 19192: 0000000008af5c94   240 FUNC    GLOBAL DEFAULT   14 criFsReadDevice_Finalize
 19200: 00000000087084b8    92 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::ChoiceFormat(icu_64::ChoiceFormat const&)
 19213: 0000000008aca7dc    60 FUNC    GLOBAL DEFAULT   14 criAfxParagraphicEqualizer_Destroy
 19218: 0000000008aebc5c   404 FUNC    GLOBAL DEFAULT   14 criFsDecodeDevice_Initialize
 19255: 00000000089c6d18   280 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice_Float32::CopyPcmDataFromEasyPlayer(unsigned int, float**, unsigned int)
 19400: 00000000087082a8    12 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::getStaticClassID()
 19417: 0000000008a67e20   276 FUNC    GLOBAL DEFAULT   14 criAtomVoice_SetSendLevelArray
 19427: 0000000008aec474    16 FUNC    GLOBAL DEFAULT   14 criFsDevice_RequestToSuspend
 19438: 0000000008a67470   104 FUNC    GLOBAL DEFAULT   14 criAtomVoice_Finalize
 19513: 000000000834d834   440 FUNC    WEAK   DEFAULT   14 physx::shdfnd::PoolBase<physx::Sq::AABBTreeIndices, physx::shdfnd::ReflectionAllocator<physx::Sq::AABBTreeIndices> >::disposeElements()
 19548: 0000000008a9a060    52 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_GetPlayerHandle
 19627: 00000000086d1950   156 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::clearCaches()
 19666: 0000000000d11de4    27 OBJECT  GLOBAL DEFAULT   10 typeinfo name for icu_64::ServiceListener
 19679: 00000000082e0038     4 FUNC    GLOBAL DEFAULT   14 physx::NpCloth::sendPvdSelfCollisionIndices()
 19918: 0000000008af64c0   600 FUNC    GLOBAL DEFAULT   14 criFsIoDevice_SelectIoInterface
 19943: 0000000008aec158   144 FUNC    GLOBAL DEFAULT   14 criFsDevice_Destroy
 19970: 000000000873df84   724 FUNC    WEAK   DEFAULT   14 icu_64::BasicCalendarFactory::create(icu_64::ICUServiceKey const&, icu_64::ICUService const*, UErrorCode&) const
 19981: 0000000008a5cfa8     8 FUNC    GLOBAL DEFAULT   14 criAsrVoice_SetTimeOffset
 20005: 0000000008a67c60    32 FUNC    GLOBAL DEFAULT   14 criAtomVoice_SetChannelVolume
 20014: 00000000086cf52c    68 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceKey::ICUServiceKey(icu_64::UnicodeString const&)
 20049: 00000000089c6178   264 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::CorrectTime(long long, int, unsigned long long&, unsigned long long&)
 20077: 0000000008a67b44   120 FUNC    GLOBAL DEFAULT   14 criAtomVoice_GetTime
 20118: 0000000008a5c6e4  1720 FUNC    GLOBAL DEFAULT   14 criAsrVoice_GenerateData
 20123: 00000000088c11b8   276 FUNC    WEAK   DEFAULT   14 OT::hb_would_apply_context_t::return_t OT::Context::dispatch<OT::hb_would_apply_context_t>(OT::hb_would_apply_context_t*) const
 20150: 00000000089c6030     4 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::CleanupAtomVoice()
 20166: 000000000873519c     4 FUNC    GLOBAL DEFAULT   14 icu_64::CalendarService::~CalendarService()
 20250: 00000000083e8344   168 FUNC    GLOBAL DEFAULT   14 physx::Sc::ClothFabricCore::getParticleIndices(unsigned int*, unsigned int) const
 20458: 00000000088c8310   404 FUNC    WEAK   DEFAULT   14 hb_sanitize_context_t::return_t OT::KernSubTable<OT::KernAATSubTableHeader>::dispatch<hb_sanitize_context_t>(hb_sanitize_context_t*) const
 20463: 0000000008a5d8a8    36 FUNC    GLOBAL DEFAULT   14 criAsrVoice_GetPacket
 20495: 0000000008a5022c    60 FUNC    GLOBAL DEFAULT   14 criAtomPlayer_GetVoiceStatus
 20543: 00000000086dd8e0     4 FUNC    GLOBAL DEFAULT   14 icu_64::ICUNumberFormatService::~ICUNumberFormatService()
 20584: 00000000088ca35c   356 FUNC    WEAK   DEFAULT   14 hb_sanitize_context_t::return_t OT::SingleSubst::dispatch<hb_sanitize_context_t>(hb_sanitize_context_t*) const
 20591: 00000000084dca00   472 FUNC    GLOBAL DEFAULT   14 physx::readIndices(unsigned int, unsigned int, unsigned int*, physx::PxInputStream&, bool)
 20695: 00000000086cf95c   316 FUNC    GLOBAL DEFAULT   14 icu_64::SimpleFactory::create(icu_64::ICUServiceKey const&, icu_64::ICUService const*, UErrorCode&) const
 20755: 0000000008708980    84 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::setChoices(double const*, signed char const*, icu_64::UnicodeString const*, int)
 20778: 00000000086cf614    12 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceKey::currentID(icu_64::UnicodeString&) const
 20870: 0000000008a8b6f4   104 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_CalculateWorkSizeForStandardVoicePool
 20917: 0000000008aebe90    12 FUNC    GLOBAL DEFAULT   14 criFsDecodeDevice_IsInitialized
 20932: 0000000008a55dd4   148 FUNC    GLOBAL DEFAULT   14 criAtomAsr_GetDeviceOutputChannels
 20942: 0000000008a693a8   428 FUNC    GLOBAL DEFAULT   14 criNcVoice_InterleavePcmFloat32toInt16
 20981: 00000000088d2608   292 FUNC    WEAK   DEFAULT   14 OT::hb_get_subtables_context_t::return_t OT::PairPos::dispatch<OT::hb_get_subtables_context_t>(OT::hb_get_subtables_context_t*) const
 21008: 0000000008a79bc4    64 FUNC    GLOBAL DEFAULT   14 criAtomParameter2_GetDeviceSendLevel
 21022: 0000000008a94af0    36 FUNC    GLOBAL DEFAULT   14 criAtomExPlayer_SetVoicePoolIdentifier
 21059: 000000000873e42c   464 FUNC    WEAK   DEFAULT   14 icu_64::DefaultCalendarFactory::create(icu_64::ICUServiceKey const&, icu_64::ICUService const*, UErrorCode&) const
 21079: 0000000008a5d534    64 FUNC    GLOBAL DEFAULT   14 criAsrVoice_UpdateDsp
 21165: 0000000008a429c0    76 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_EnumerateActiveVoices
 21179: 00000000086d2214    16 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::get(icu_64::Locale const&, icu_64::Locale*, UErrorCode&) const
 21230: 0000000008a2793c   124 FUNC    GLOBAL DEFAULT   14 criAtomConfig_FindVoiceLimitGroup
 21290: 0000000008a67fbc    88 FUNC    GLOBAL DEFAULT   14 criAtomVoice_SetDspParameter
 21342: 00000000084dc89c   356 FUNC    GLOBAL DEFAULT   14 physx::storeIndices(unsigned int, unsigned int, unsigned int const*, physx::PxOutputStream&, bool)
 21390: 00000000088d2010   124 FUNC    WEAK   DEFAULT   14 hb_sanitize_context_t::return_t OT::ExtensionFormat1<OT::ExtensionPos>::dispatch<hb_sanitize_context_t>(hb_sanitize_context_t*) const
 21425: 00000000089c6924    20 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::SetSoundRendererType(CriAtomSoundRendererTypeTag)
 21429: 0000000008a5d790   104 FUNC    GLOBAL DEFAULT   14 criAsrVoice_GetDspParameter
 21433: 0000000008afd55c   136 FUNC    GLOBAL DEFAULT   14 MovieDecoder_StartStreamingEsCore(MovieDecoderStruct*, char const**, int, unsigned int)
 21526: 0000000008a681c0    68 FUNC    GLOBAL DEFAULT   14 criAtomVoice_SetSpatializer
 21586: 0000000008a5cfb0    68 FUNC    GLOBAL DEFAULT   14 criAsrVoice_GetTime
 21604: 00000000086d41a0   196 FUNC    GLOBAL DEFAULT   14 icu_64::ICUResourceBundleFactory::handleCreate(icu_64::Locale const&, int, icu_64::ICUService const*, UErrorCode&) const
 21612: 0000000008b12b68     8 FUNC    GLOBAL DEFAULT   14 criVsd_GetLicense
 21658: 000000000873e5fc    28 FUNC    WEAK   DEFAULT   14 icu_64::CalendarService::isDefault() const
 21719: 00000000086cfe20   252 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::~ICUService()
 21732: 0000000008a8a454   276 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_AllocateAdxVoicePool
 21737: 0000000008a5d448    68 FUNC    GLOBAL DEFAULT   14 criAsrVoice_SetRouting
 21765: 0000000008b12b70     4 FUNC    GLOBAL DEFAULT   14 criVsd_ClearLicense
 21848: 0000000008a5dae0   248 FUNC    GLOBAL DEFAULT   14 criAsrVoiceList_Execute
 21875: 00000000083860f0    92 FUNC    GLOBAL DEFAULT   14 non-virtual thunk to physx::cloth::ClothImpl<physx::cloth::SwCloth>::setSelfCollisionIndices(physx::cloth::Range<unsigned int const>)
 21905: 0000000008a6807c    88 FUNC    GLOBAL DEFAULT   14 criAtomVoice_SetRouting
 21954: 00000000089c69cc    12 FUNC    WEAK   DEFAULT   14 non-virtual thunk to CriManaSoundAtomVoice::~CriManaSoundAtomVoice()
 21986: 00000000086d17c0   204 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::reset()
 21989: 0000000008a99ba8   128 FUNC    GLOBAL DEFAULT   14 criAtomEx_MonitoringVoiceStop
 22167: 0000000008a5c5e8   152 FUNC    GLOBAL DEFAULT   14 criAsrVoiceList_RemoveVoice
 22203: 00000000087089d4   972 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::setChoices(double const*, signed char const*, icu_64::UnicodeString const*, int, UErrorCode&)
 22228: 000000000834d9ec   920 FUNC    WEAK   DEFAULT   14 void physx::shdfnd::sort<void*, physx::shdfnd::Less<void*>, physx::shdfnd::ReflectionAllocator<physx::Sq::AABBTreeIndices> >(void**, unsigned int, physx::shdfnd::Less<void*> const&, physx::shdfnd::ReflectionAllocator<physx::Sq::AABBTreeIndices> const&, unsigned int)
 22272: 00000000086cf5a4    60 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceKey::~ICUServiceKey()
 22443: 00000000088d08ec   844 FUNC    WEAK   DEFAULT   14 hb_sanitize_context_t::return_t OT::PosLookupSubTable::dispatch<hb_sanitize_context_t>(hb_sanitize_context_t*, unsigned int) const
 22451: 0000000008a63394   124 FUNC    GLOBAL DEFAULT   14 criNcMic_GetDeviceInfo
 22501: 0000000000d11dff    25 OBJECT  GLOBAL DEFAULT   10 typeinfo name for icu_64::ICUServiceKey
 22504: 0000000008a33f00     4 FUNC    GLOBAL DEFAULT   14 criAtomExAcb_GetDeviceSendLevelParametersInfoByCueIndex
 22545: 0000000008a44628    32 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_SetVoiceEventCallback
 22572: 0000000008af9f1c    36 FUNC    GLOBAL DEFAULT   14 criVip_SetAtomVoicePoolID
 22619: 00000000086def60    28 FUNC    WEAK   DEFAULT   14 icu_64::ICUNumberFormatService::isDefault() const
 22764: 00000000086cf84c    12 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceKey::getStaticClassID()
 22779: 000000000833a9f4   288 FUNC    GLOBAL DEFAULT   14 physx::Pt::SpatialHash::reorderParticleIndicesToCells(physx::Pt::Particle const*, unsigned int, physx::Pt::ParticleCell*, unsigned int*, unsigned int, unsigned short*)
 22787: 0000000008a564c4    84 FUNC    GLOBAL DEFAULT   14 criAtomAsr_AddAsrVoice
 22844: 00000000089c6e3c    12 FUNC    WEAK   DEFAULT   14 non-virtual thunk to CriManaSoundAtomVoice_Float32::~CriManaSoundAtomVoice_Float32()
 22859: 00000000088da1dc   548 FUNC    WEAK   DEFAULT   14 hb_sanitize_context_t::return_t AAT::ChainSubtable<AAT::ObsoleteTypes>::dispatch<hb_sanitize_context_t>(hb_sanitize_context_t*) const
 22908: 0000000008a7c108    12 FUNC    GLOBAL DEFAULT   14 criAtom3dPos_GetMinVoicePriority
 22937: 00000000083e7fd0    16 FUNC    GLOBAL DEFAULT   14 physx::Sc::ClothFabricCore::getNbParticleIndices() const
 22985: 00000000087085b8    84 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::operator==(icu_64::Format const&) const
 23028: 00000000086cfbf4     4 FUNC    GLOBAL DEFAULT   14 icu_64::ServiceListener::~ServiceListener()
 23057: 0000000000d12392    34 OBJECT  GLOBAL DEFAULT   10 typeinfo name for icu_64::ICUNumberFormatService
 23117: 0000000008a68284    16 FUNC    GLOBAL DEFAULT   14 criAtomVoice_GetOutputGranularity
 23128: 0000000008aec498     8 FUNC    GLOBAL DEFAULT   14 criFsDevice_GetServerHandle
 23131: 0000000000d12ff2    24 OBJECT  GLOBAL DEFAULT   10 typeinfo name for icu_64::ChoiceFormat
 23151: 00000000086cff20   112 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::get(icu_64::UnicodeString const&, UErrorCode&) const
 23165: 0000000008755bbc     4 FUNC    GLOBAL DEFAULT   14 icu_64::ICUCollatorService::~ICUCollatorService()
 23171: 00000000088ca4c0   324 FUNC    WEAK   DEFAULT   14 hb_sanitize_context_t::return_t OT::MultipleSubst::dispatch<hb_sanitize_context_t>(hb_sanitize_context_t*) const
 23201: 000000000988edd0   208 OBJECT  GLOBAL DEFAULT   16 vtable for icu_64::ICUBreakIteratorService
 23202: 0000000008a5d2e4   320 FUNC    GLOBAL DEFAULT   14 criAsrVoice_Update
 23223: 0000000008a8b75c   276 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_AllocateStandardVoicePool
 23227: 0000000008a1d920    64 FUNC    GLOBAL DEFAULT   14 criStreamerManager_SetFreeTimeBufferingFlagByDeviceId
 23258: 0000000008a5d1c4   288 FUNC    GLOBAL DEFAULT   14 criAsrVoice_Setup
 23281: 0000000008a9ebcc   164 FUNC    GLOBAL DEFAULT   14 criAtomExCategory_SetDeviceSend
 23360: 00000000086d001c    12 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::getKey(icu_64::ICUServiceKey&, icu_64::UnicodeString*, UErrorCode&) const
 23379: 00000000088d80b8   740 FUNC    WEAK   DEFAULT   14 OT::hb_ot_apply_context_t::return_t OT::PosLookupSubTable::dispatch<OT::hb_ot_apply_context_t>(OT::hb_ot_apply_context_t*, unsigned int) const
 23457: 00000000089c6680   504 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::SetBusSendLevel(char const*, float)
 23510: 0000000009891088   168 OBJECT  GLOBAL DEFAULT   16 vtable for icu_64::ICUService
 23525: 0000000008a6d8f4    12 FUNC    GLOBAL DEFAULT   14 criNcvPseudo_GetNumVoices
 23533: 00000000086d1a60    24 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::notifyListener(icu_64::EventListener&) const
 23618: 00000000086decbc   280 FUNC    WEAK   DEFAULT   14 icu_64::NFFactory::create(icu_64::ICUServiceKey const&, icu_64::ICUService const*, UErrorCode&) const
 23620: 0000000008a8abc0   108 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_CalculateWorkSizeForRawPcmVoicePool
 23642: 0000000008a67a28    84 FUNC    GLOBAL DEFAULT   14 criAtomVoice_Destroy
 23669: 00000000083e48c0    20 FUNC    GLOBAL DEFAULT   14 physx::Sc::ClothCore::setSelfCollisionIndices(unsigned int const*, unsigned int)
 23708: 0000000000d11de2     2 OBJECT  GLOBAL DEFAULT   10 icu_64::ICUServiceKey::PREFIX_DELIMITER
 23722: 00000000086d2714   100 FUNC    WEAK   DEFAULT   14 icu_64::ServiceEnumeration::count(UErrorCode&) const
 23759: 0000000008a1d9b4    12 FUNC    GLOBAL DEFAULT   14 criStreamerManager_GetDeviceSpecForTools
 23803: 0000000008aec1e8   304 FUNC    GLOBAL DEFAULT   14 criFsDevice_Create
 23869: 000000000834dd84   268 FUNC    WEAK   DEFAULT   14 physx::shdfnd::Array<void*, physx::shdfnd::ReflectionAllocator<physx::Sq::AABBTreeIndices> >::growAndPushBack(void* const&)
 23926: 0000000008a5d024   416 FUNC    GLOBAL DEFAULT   14 criAsrVoice_SetMatrix
 23981: 0000000009891130    24 OBJECT  GLOBAL DEFAULT   16 typeinfo for icu_64::ServiceListener
 23996: 000000000833c368    52 FUNC    GLOBAL DEFAULT   14 physx::Sq::AABBTree::shiftIndices(unsigned int)
 24011: 0000000008a675b4   132 FUNC    GLOBAL DEFAULT   14 criAtomVoice_CalculateWorkSize
 24063: 00000000087088a8    56 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::applyPattern(icu_64::UnicodeString const&, UErrorCode&)
 24114: 0000000008af5e44    44 FUNC    GLOBAL DEFAULT   14 criFsReadDevice_SetDeviceEnabled
 24212: 00000000089c6b10     8 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice_Float32::GetPcmFormat()
 24213: 0000000008a1d7f4   196 FUNC    GLOBAL DEFAULT   14 criStreamerManager_UpdateStreamerBpsByDeviceId
 24254: 0000000008a56bb4   440 FUNC    GLOBAL DEFAULT   14 criAmbisonics_CalculateCoefficent
 24288: 00000000086d2208    12 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::get(icu_64::Locale const&, int, UErrorCode&) const
 24333: 0000000000d11e94    28 OBJECT  GLOBAL DEFAULT   10 typeinfo name for icu_64::ICULocaleService
 24347: 00000000088d58d8   228 FUNC    WEAK   DEFAULT   14 hb_sanitize_context_t::return_t AAT::ChainSubtable<AAT::ExtendedTypes>::dispatch<hb_sanitize_context_t>(hb_sanitize_context_t*) const
 24419: 00000000087086cc   312 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::dtos(double, icu_64::UnicodeString&)
 24436: 00000000089c6280   104 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::Start()
 24549: 0000000008a68a50   164 FUNC    GLOBAL DEFAULT   14 criNcVoice_CalculateWorkSizeForLibrary
 24585: 00000000098913f0    24 OBJECT  GLOBAL DEFAULT   16 typeinfo for icu_64::ICULocaleService
 24601: 00000000086d09ec   372 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::getVisibleIDMap(UErrorCode&) const
 24715: 0000000008a67130   300 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_DetachSpatializer
 24819: 00000000089c6938     8 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::SetAsrRackId(int)
 24838: 00000000088d79c0   812 FUNC    WEAK   DEFAULT   14 OT::hb_ot_apply_context_t::return_t OT::SubstLookupSubTable::dispatch<OT::hb_ot_apply_context_t>(OT::hb_ot_apply_context_t*, unsigned int) const
 24875: 0000000008a67de8    56 FUNC    GLOBAL DEFAULT   14 criAtomVoice_SetSendLevel
 24909: 00000000086d3cc4   252 FUNC    GLOBAL DEFAULT   14 icu_64::LocaleKeyFactory::create(icu_64::ICUServiceKey const&, icu_64::ICUService const*, UErrorCode&) const
 24935: 00000000086dd8e0     4 FUNC    GLOBAL DEFAULT   14 icu_64::ICUNumberFormatService::~ICUNumberFormatService()
 25009: 0000000008a67530    12 FUNC    GLOBAL DEFAULT   14 criAtomVoice_IsInitialized
 25043: 0000000008a4470c    12 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_IsEnableCalculationAisacControlFrom3dPosition
 25071: 00000000086d12fc   316 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::registerInstance(icu_64::UObject*, icu_64::UnicodeString const&, signed char, UErrorCode&)
 25193: 0000000008a5d7f8    56 FUNC    GLOBAL DEFAULT   14 criAsrVoice_SetInsertionDsp
 25198: 0000000008a67b20    36 FUNC    GLOBAL DEFAULT   14 criAtomVoice_GetStatus
 25262: 0000000008a95d8c   104 FUNC    GLOBAL DEFAULT   14 criAtomExPlayback_SetVoicePriority
 25284: 00000000089984ec    60 FUNC    GLOBAL DEFAULT   14 CriMvEasyPlayer::attachCenterVoice()
 25456: 0000000008af5f80   180 FUNC    GLOBAL DEFAULT   14 criFsReadDevice_RequestToSuspendAll
 25462: 00000000082e2bf4     8 FUNC    GLOBAL DEFAULT   14 physx::NpClothFabric::getParticleIndices(unsigned int*, unsigned int) const
 25469: 0000000008a44484    20 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_SetFilterCallback
 25477: 0000000008a6b774    32 FUNC    GLOBAL DEFAULT   14 criNcvHcaMx_GetOutputNcVoice
 25529: 0000000008694528   308 FUNC    GLOBAL DEFAULT   14 utext_openConstUnicodeString_64
 25606: 0000000008a34218    48 FUNC    GLOBAL DEFAULT   14 criAtomExAcb_GetDeviceSendLevelParametersInfoByCueId
 25665: 00000000082e00a4     8 FUNC    GLOBAL DEFAULT   14 physx::NpCloth::getNbSelfCollisionIndices() const
 25678: 0000000008a43ffc    16 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_SetPriority
 25772: 0000000008a8b348    92 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_CalculateWorkSizeForHcaMxVoicePool
 25783: 000000000834c658    60 FUNC    GLOBAL DEFAULT   14 physx::Sq::IncrementalAABBTree::fixupTreeIndices(physx::Sq::IncrementalAABBTreeNode*, unsigned int, unsigned int)
 25962: 00000000083e3fd4   112 FUNC    GLOBAL DEFAULT   14 physx::Sc::ClothCore::getSelfCollisionIndices(unsigned int*) const
 26142: 00000000086cfe20   252 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::~ICUService()
 26174: 000000000996a16c   256 OBJECT  GLOBAL DEFAULT   22 crifs_device_info
 26320: 0000000008534a2c    20 FUNC    WEAK   DEFAULT   14 physx::Gu::ConvexMesh::getVertices() const
 26385: 00000000089c69c8     4 FUNC    WEAK   DEFAULT   14 non-virtual thunk to CriManaSoundAtomVoice::~CriManaSoundAtomVoice()
 26408: 0000000008789470   116 FUNC    GLOBAL DEFAULT   14 icu_64::CollationFastLatinBuilder::getMiniCE(long) const
 26516: 00000000089c7c80    36 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomEx::SetDefaultConfigForManaSoundVoicePool(CriAtomExRawPcmVoicePoolConfigTag*)
 26547: 00000000087093d4   132 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::clone() const
 26571: 0000000008a68104    60 FUNC    GLOBAL DEFAULT   14 criAtomVoice_GetNumRoutings
 26616: 000000000868b6f8    16 FUNC    WEAK   DEFAULT   14 icu_64::ICUBreakIteratorFactory::handleCreate(icu_64::Locale const&, int, icu_64::ICUService const*, UErrorCode&) const
 26630: 00000000086d1a78    44 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::getName(icu_64::UnicodeString&) const
 26733: 00000000086cf570    52 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceKey::~ICUServiceKey()
 26734: 000000000870860c    72 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::operator=(icu_64::ChoiceFormat const&)
 26764: 00000000086d0dd8    68 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::getDisplayNames(icu_64::UVector&, UErrorCode&) const
 26768: 0000000008ac9fb8    12 FUNC    GLOBAL DEFAULT   14 criAfxParagraphicEqualizer_GetEffectName
 26809: 0000000008ab9ebc   356 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_AllocateInstrumentVoicePool
 26926: 0000000009897cc0    24 OBJECT  GLOBAL DEFAULT   16 typeinfo for icu_64::ICUCollatorService
 26936: 0000000008709178   280 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::parseArgument(icu_64::MessagePattern const&, int, icu_64::UnicodeString const&, icu_64::ParsePosition&)
 26947: 0000000008a1d158    12 FUNC    GLOBAL DEFAULT   14 criStreamerManager_SetDefaultDeviceId
 26983: 00000000089c69e0   160 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice_Float32::CalculateOutputWorkSize(unsigned int, unsigned int)
 27004: 0000000008a66eac   644 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_AttachSpatializer
 27057: 00000000086d2468   168 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::getAvailableLocales() const
 27079: 000000000a570218    24 OBJECT  GLOBAL DEFAULT   23 CriManaSoundAtomVoice::s_sndout_list
 27082: 0000000008999a94    20 FUNC    GLOBAL DEFAULT   14 CriMvEasyPlayer::ReplaceCenterVoice(int, CriError&)
 27098: 000000000988eea0    24 OBJECT  GLOBAL DEFAULT   16 typeinfo for icu_64::ICUBreakIteratorService
 27209: 0000000008a4400c    20 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_BreakLoop
 27317: 00000000089c6e38     4 FUNC    WEAK   DEFAULT   14 non-virtual thunk to CriManaSoundAtomVoice_Float32::~CriManaSoundAtomVoice_Float32()
 27320: 00000000086d12e8    20 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::registerInstance(icu_64::UObject*, icu_64::UnicodeString const&, UErrorCode&)
 27372: 0000000008981394   960 FUNC    GLOBAL DEFAULT   14 silk_decode_indices
 27383: 0000000008708514   164 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::ChoiceFormat(icu_64::UnicodeString const&, UParseError&, UErrorCode&)
 27423: 00000000086d2778   128 FUNC    WEAK   DEFAULT   14 icu_64::ServiceEnumeration::snext(UErrorCode&)
 27431: 0000000008a5d4a4     8 FUNC    GLOBAL DEFAULT   14 criAsrVoice_IsDropped
 27434: 0000000008a3db98    72 FUNC    GLOBAL DEFAULT   14 criAtomTblVoiceLimitGroup_Initialize
 27489: 00000000086cf734     8 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceKey::prefix(icu_64::UnicodeString&) const
 27492: 0000000008708da0    12 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::getLimits(int&) const
 27498: 00000000086cfbf4     4 FUNC    GLOBAL DEFAULT   14 icu_64::ServiceListener::~ServiceListener()
 27616: 00000000089c6940    40 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::GetAtomExPlayer()
 27623: 0000000008755bbc     4 FUNC    GLOBAL DEFAULT   14 icu_64::ICUCollatorService::~ICUCollatorService()
 27658: 0000000008a94904    56 FUNC    GLOBAL DEFAULT   14 criAtomExPlayer_SetVoicePriority
 27672: 00000000098912b8   208 OBJECT  GLOBAL DEFAULT   16 vtable for icu_64::ICULocaleService
 27707: 00000000083cc5bc   980 FUNC    GLOBAL DEFAULT   14 physx::Dy::createSolverTaskChain(physx::Dy::DynamicsContext&, physx::Dy::SolverIslandObjects const&, physx::PxsIslandIndices const&, unsigned int, physx::IG::SimpleIslandManager&, unsigned int*, physx::PxsMaterialManager*, physx::PxBaseTask*, physx::PxsContactManagerOutputIterator&, bool)
 27717: 000000000873e618    88 FUNC    WEAK   DEFAULT   14 icu_64::CalendarService::cloneInstance(icu_64::UObject*) const
 27890: 0000000008af5954   832 FUNC    GLOBAL DEFAULT   14 criFs_AttachIoDevice
 27898: 0000000008a42b68    12 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_ClearFinalVoiceParameter
 27913: 0000000008540404   412 FUNC    GLOBAL DEFAULT   14 physx::getVertexEdgeIndices(physx::Gu::HeightField const&, unsigned int, unsigned int, unsigned int, physx::EdgeData*)
 27986: 0000000008afd8ac    12 FUNC    GLOBAL DEFAULT   14 MovieDecoder_SetAudioOutputDeviceConfig
 27990: 000000000828b4a8    52 FUNC    GLOBAL DEFAULT   14 virt_voicepos
 28007: 0000000008af67f4   100 FUNC    GLOBAL DEFAULT   14 criFsIoDevice_SetSelectIoCallback
 28030: 0000000008af5768   388 FUNC    GLOBAL DEFAULT   14 criFsReadDevice_Initialize
 28090: 0000000008a6de9c     8 FUNC    GLOBAL DEFAULT   14 criAtomInstrumentVoice_CalculateWorkSizeForLibrary
 28110: 0000000008a5cd9c     8 FUNC    GLOBAL DEFAULT   14 criAsrVoice_OutputToChStrip
 28222: 00000000082e2bcc     8 FUNC    GLOBAL DEFAULT   14 physx::NpClothFabric::getNbParticleIndices() const
 28248: 00000000086d262c    64 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::createKey(icu_64::UnicodeString const*, int, UErrorCode&) const
 28300: 0000000008a99eb8   280 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_Free
 28326: 0000000008aacaac   184 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_AttachDspPitchShifter
 28369: 00000000086d28fc   268 FUNC    WEAK   DEFAULT   14 icu_64::ServiceEnumeration::ServiceEnumeration(icu_64::ServiceEnumeration const&, UErrorCode&)
 28507: 0000000008adb5b0    96 FUNC    GLOBAL DEFAULT   14 criFs_GetDeviceInfo
 28531: 0000000008b112dc    20 FUNC    GLOBAL DEFAULT   14 criVsd_EnableVoicePoolCreate
 28604: 00000000089c6e30     8 FUNC    WEAK   DEFAULT   14 CriManaSoundAtomVoice_Float32::~CriManaSoundAtomVoice_Float32()
 28607: 00000000086d0ba0   568 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::getDisplayName(icu_64::UnicodeString const&, icu_64::UnicodeString&, icu_64::Locale const&) const
 28624: 0000000009891408    24 OBJECT  GLOBAL DEFAULT   16 typeinfo for icu_64::ServiceEnumeration
 28820: 0000000008ab617c     4 FUNC    GLOBAL DEFAULT   14 criAtomExAsrRack_GetOutputDeviceChannels
 28840: 00000000088d7cec   324 FUNC    WEAK   DEFAULT   14 OT::hb_ot_apply_context_t::return_t OT::ChainContext::dispatch<OT::hb_ot_apply_context_t>(OT::hb_ot_apply_context_t*) const
 28928: 00000000088d0d30   212 FUNC    WEAK   DEFAULT   14 OT::ValueFormat::sanitize_value_devices(hb_sanitize_context_t*, void const*, OT::IntType<unsigned short, 2u> const*) const
 29007: 0000000008a271fc   224 FUNC    GLOBAL DEFAULT   14 criAtomConfig_GetVoiceLimitGroupInformation
 29042: 0000000008708514   164 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::ChoiceFormat(icu_64::UnicodeString const&, UParseError&, UErrorCode&)
 29159: 0000000008aebf08    12 FUNC    GLOBAL DEFAULT   14 criFsDecodeDevice_ExecuteServer
 29275: 00000000098911d0    48 OBJECT  GLOBAL DEFAULT   16 vtable for icu_64::ServiceListener
 29299: 0000000008a3dc58    36 FUNC    GLOBAL DEFAULT   14 criAtomTblVoiceLimitGroup_GetItemIndex
 29346: 0000000008ac9f94    12 FUNC    GLOBAL DEFAULT   14 criAfxParagraphicEqualizer_GetInterfaceWithVersion
 29489: 0000000008aec368    12 FUNC    GLOBAL DEFAULT   14 criFsDevice_RemoveTask
 29515: 0000000008a1daac    36 FUNC    GLOBAL DEFAULT   14 criStreamerManager_SetDeviceConfig
 29520: 0000000000d16670    30 OBJECT  GLOBAL DEFAULT   10 typeinfo name for icu_64::ICUCollatorService
 29540: 0000000008a5d8a0     8 FUNC    GLOBAL DEFAULT   14 criAsrVoice_SetCallback
 29683: 00000000098ba740   304 OBJECT  GLOBAL DEFAULT   16 vtable for CriManaSoundAtomVoice_Float32
 29703: 00000000084dcd3c   728 FUNC    GLOBAL DEFAULT   14 physx::Gu::ReadIndices(unsigned int, unsigned int, unsigned int*, physx::PxInputStream&, bool)
 29739: 0000000008a6c544   132 FUNC    GLOBAL DEFAULT   14 criNcHcaMixer_AddVoice
 29747: 000000000868b724    16 FUNC    WEAK   DEFAULT   14 icu_64::ICUBreakIteratorService::cloneInstance(icu_64::UObject*) const
 29763: 00000000086d22f0    24 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::registerInstance(icu_64::UObject*, icu_64::Locale const&, UErrorCode&)
 29771: 0000000008a99ff4   108 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_GetNumUsedVoices
 29777: 00000000086d3dc0   196 FUNC    GLOBAL DEFAULT   14 icu_64::LocaleKeyFactory::handlesKey(icu_64::ICUServiceKey const&, UErrorCode&) const
 29792: 00000000083383a0   464 FUNC    WEAK   DEFAULT   14 physx::Pt::HeightFieldAabbTest::getTriangleVertices(physx::PxVec3*, physx::Pt::HeightFieldAabbTest::Iterator const&) const
 29818: 0000000008560800    52 FUNC    GLOBAL DEFAULT   14 physx::Gu::TriangleMesh::getVerticesForModification()
 29829: 00000000082468f4    36 FUNC    GLOBAL DEFAULT   14 std::__ndk1::random_device::~random_device()
 29853: 0000000008aec374    32 FUNC    GLOBAL DEFAULT   14 criFsDevice_Execute
 29893: 0000000008aca10c   560 FUNC    GLOBAL DEFAULT   14 criAfxParagraphicEqualizer_Create
 29948: 0000000008a98ca8   232 FUNC    GLOBAL DEFAULT   14 criAtomExPlayback_MonitoringVoiceStop
 30074: 0000000008af5df0     8 FUNC    GLOBAL DEFAULT   14 criFsReadDevice_CalculateWorkSizeForCreateHandle
 30123: 00000000028322c8  2888 FUNC    GLOBAL DEFAULT   14 Java_com_epicgames_ue4_NativeCalls_RouteServiceIntent
 30148: 00000000085a4a1c    48 FUNC    GLOBAL DEFAULT   14 physx::shdfnd::atomicExchange(int volatile*, int)
 30193: 0000000008a8a7b0   104 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_CalculateWorkSizeForWaveVoicePool
 30227: 00000000084d3d48   128 FUNC    GLOBAL DEFAULT   14 physx::Gu::computeBoundsAroundVertices(physx::PxBounds3&, unsigned int, physx::PxVec3 const*)
 30276: 0000000008a8a818   276 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_AllocateWaveVoicePool
 30408: 00000000089c65f8   136 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::SetBusSendLevel(int, float)
 30464: 00000000086d2858   164 FUNC    WEAK   DEFAULT   14 icu_64::ServiceEnumeration::ServiceEnumeration(icu_64::ICULocaleService const*, UErrorCode&)
 30585: 000000000841e068    12 FUNC    GLOBAL DEFAULT   14 getNbPxClothFabric_ParticleIndices(physx::PxClothFabric const*)
 30611: 000000000837e5b4    20 FUNC    GLOBAL DEFAULT   14 non-virtual thunk to physx::cloth::SwFactory::extractSelfCollisionIndices(physx::cloth::Cloth const&, physx::cloth::Range<unsigned int>) const
 30628: 0000000008a68a38    24 FUNC    GLOBAL DEFAULT   14 criNcVoice_IsInterfaceRegistered
 30674: 00000000086d1438   172 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::createSimpleFactory(icu_64::UObject*, icu_64::UnicodeString const&, signed char, UErrorCode&)
 30711: 0000000008ab9a14   104 FUNC    GLOBAL DEFAULT   14 criAtomExVoicePool_CalculateWorkSizeForAiffVoicePool
 30723: 0000000008756b94   196 FUNC    GLOBAL DEFAULT   14 icu_64::CFactory::create(icu_64::ICUServiceKey const&, icu_64::ICUService const*, UErrorCode&) const
 30764: 0000000008af5e70    92 FUNC    GLOBAL DEFAULT   14 criFsReadDevice_GetDeviceHandle
 30847: 00000000083dc3a4    48 FUNC    GLOBAL DEFAULT   14 physx::Sc::ShapeCore::getMaterialIndices() const
 30945: 0000000008a67c80    20 FUNC    GLOBAL DEFAULT   14 criAtomVoice_SetPitch
 30952: 0000000008aca720   188 FUNC    GLOBAL DEFAULT   14 criAfxParagraphicEqualizer_ApplyParameters
 30978: 0000000009897bf0   208 OBJECT  GLOBAL DEFAULT   16 vtable for icu_64::ICUCollatorService
 31034: 0000000008a42994    44 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_Finalize
 31042: 00000000087575c8    28 FUNC    WEAK   DEFAULT   14 icu_64::ICUCollatorService::isDefault() const
 31105: 00000000082469ac    88 FUNC    GLOBAL DEFAULT   14 std::__ndk1::random_device::entropy() const
 31135: 00000000086cf570    52 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceKey::~ICUServiceKey()
 31166: 0000000008a5d884    20 FUNC    GLOBAL DEFAULT   14 criAsrVoice_SetRendererType
 31194: 00000000088d24e4   292 FUNC    WEAK   DEFAULT   14 OT::hb_get_subtables_context_t::return_t OT::SinglePos::dispatch<OT::hb_get_subtables_context_t>(OT::hb_get_subtables_context_t*) const
 31226: 0000000008a67268   176 FUNC    GLOBAL DEFAULT   14 criAtomVoice_CalculateWorkSizeForLibrary
 31258: 0000000000d11eb0    30 OBJECT  GLOBAL DEFAULT   10 typeinfo name for icu_64::ServiceEnumeration
 31283: 0000000008aec4b8    36 FUNC    GLOBAL DEFAULT   14 criFsDevice_SetThreadPriorityCallback
 31301: 0000000008a587b8     8 FUNC    GLOBAL DEFAULT   14 criAsrRack_GetOutputNcVoiceType
 31303: 0000000008aca854    60 FUNC    GLOBAL DEFAULT   14 criAfxParagraphicEqualizer_Start
 31365: 0000000008a680d4    48 FUNC    GLOBAL DEFAULT   14 criAtomVoice_ResetRouting
 31416: 0000000008a69058   260 FUNC    GLOBAL DEFAULT   14 criNcVoice_InterleavePcm16
 31422: 0000000008adb610    92 FUNC    GLOBAL DEFAULT   14 criFs_SetDeviceInfo
 31491: 0000000008a6df38    36 FUNC    GLOBAL DEFAULT   14 criAtomInstrumentVoice_Finalize
 31514: 00000000087f2da4   412 FUNC    GLOBAL DEFAULT   14 icu_64::number::impl::NumberStringBuilder::splice(int, int, icu_64::UnicodeString const&, int, int, unsigned char, UErrorCode&)
 31548: 0000000008708df4   404 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::format(double, icu_64::UnicodeString&, icu_64::FieldPosition&) const
 31637: 0000000008a67318   344 FUNC    GLOBAL DEFAULT   14 criAtomVoice_Initialize
 31643: 0000000008a6915c   588 FUNC    GLOBAL DEFAULT   14 criNcVoice_InterleavePcm32
 31680: 0000000008a67b18     8 FUNC    GLOBAL DEFAULT   14 criAtomVoice_IsPaused
 31746: 00000000084dcbd8   356 FUNC    GLOBAL DEFAULT   14 physx::Gu::StoreIndices(unsigned int, unsigned int, unsigned int const*, physx::PxOutputStream&, bool)
 31800: 00000000086cf5e8    44 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceKey::canonicalID(icu_64::UnicodeString&) const
 31816: 00000000086cf6ac     8 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceKey::fallback()
 31818: 0000000008a5cdac    12 FUNC    GLOBAL DEFAULT   14 criAsrVoice_IsPlaying
 31834: 0000000008a99c70    44 FUNC    GLOBAL DEFAULT   14 criAtomEx_SetMonitoringVoiceStopPlaybackId
 31961: 0000000008a68044    56 FUNC    GLOBAL DEFAULT   14 criAtomVoice_UpdateDsp
 32016: 0000000008a69554   440 FUNC    GLOBAL DEFAULT   14 criNcVoice_InterleavePcmFloat32toInt32V24
 32078: 0000000008a56518   104 FUNC    GLOBAL DEFAULT   14 criAtomAsr_GetOutputNcVoiceType
 32097: 0000000008a7a828    60 FUNC    GLOBAL DEFAULT   14 criAtomParameter2_GetVoicePoolIdentifier
 32117: 00000000086cfc08    12 FUNC    GLOBAL DEFAULT   14 icu_64::ServiceListener::getDynamicClassID() const
 32137: 0000000008a5cff4    20 FUNC    GLOBAL DEFAULT   14 criAsrVoice_GetNumBufferedSamples
 32190: 00000000088c12cc   504 FUNC    WEAK   DEFAULT   14 OT::hb_would_apply_context_t::return_t OT::ChainContext::dispatch<OT::hb_would_apply_context_t>(OT::hb_would_apply_context_t*) const
 32292: 000000000875753c   140 FUNC    WEAK   DEFAULT   14 icu_64::ICUCollatorService::getKey(icu_64::ICUServiceKey&, icu_64::UnicodeString*, UErrorCode&) const
 32348: 0000000008a5cf98    16 FUNC    GLOBAL DEFAULT   14 criAsrVoice_Flush
 32456: 000000000a570cf8    24 OBJECT  GLOBAL DEFAULT   23 criatomsoundvoice_active_voice_list
 32466: 000000000837e5a0    20 FUNC    GLOBAL DEFAULT   14 physx::cloth::SwFactory::extractSelfCollisionIndices(physx::cloth::Cloth const&, physx::cloth::Range<unsigned int>) const
 32475: 000000000a570d10     8 OBJECT  GLOBAL DEFAULT   23 criatomsoundvoice_total_info
 32552: 00000000088bc3a0   184 FUNC    WEAK   DEFAULT   14 OT::Device::get_x_delta(hb_font_t*, OT::VariationStore const&) const
 32612: 00000000086d1f58   108 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::ICULocaleService()
 32760: 00000000089c645c    24 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::GetVolume()
 32768: 00000000089c7ca4    52 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomEx::UpdateConfigForManaSoundVoicePool(CriAtomExRawPcmVoicePoolConfigTag*, int, int)
 32785: 0000000008a67c3c     8 FUNC    GLOBAL DEFAULT   14 criAtomVoice_SetVolumeBias
 32786: 00000000086d2078    16 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::get(icu_64::Locale const&, UErrorCode&) const
 32828: 00000000098ba610   304 OBJECT  GLOBAL DEFAULT   16 vtable for CriManaSoundAtomVoice
 32911: 0000000008708354   172 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::ChoiceFormat(double const*, icu_64::UnicodeString const*, int)
 32933: 0000000008a44470    20 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_SetDataRequestCallback
 32970: 00000000089c69dc     4 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice_Float32::Destroy()
 33000: 00000000086bca98   196 FUNC    GLOBAL DEFAULT   14 icu_64::PossibleWord::candidates(UText*, icu_64::DictionaryMatcher*, int)
 33047: 0000000008aebe9c    16 FUNC    GLOBAL DEFAULT   14 criFsDecodeDevice_GetDeviceHandle
 33061: 000000000841e05c    12 FUNC    GLOBAL DEFAULT   14 getPxClothFabric_ParticleIndices(physx::PxClothFabric const*, unsigned int*, unsigned int)
 33071: 00000000088c7030   328 FUNC    WEAK   DEFAULT   14 OT::Device::sanitize(hb_sanitize_context_t*) const
 33107: 0000000008629288    60 FUNC    GLOBAL DEFAULT   14 udata_openChoice_64
 33226: 0000000008a67568    76 FUNC    GLOBAL DEFAULT   14 criAtomVoice_ExecuteServer
 33252: 0000000008a68bc4    88 FUNC    GLOBAL DEFAULT   14 criNcVoice_Finalize
 33324: 00000000086cf868     4 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceFactory::~ICUServiceFactory()
 33465: 0000000008a55ee4    28 FUNC    GLOBAL DEFAULT   14 criAtomPlayer_GetAsrVoiceHn
 33515: 00000000086d2074     4 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::~ICULocaleService()
 33529: 00000000086d2510   236 FUNC    GLOBAL DEFAULT   14 icu_64::ICULocaleService::validateFallbackLocale() const
 33613: 0000000008383294     8 FUNC    WEAK   DEFAULT   14 non-virtual thunk to physx::cloth::ClothImpl<physx::cloth::SwCloth>::getNumSelfCollisionIndices() const
 33662: 000000000824684c   168 FUNC    GLOBAL DEFAULT   14 std::__ndk1::random_device::random_device(std::__ndk1::basic_string<char, std::__ndk1::char_traits<char>, std::__ndk1::allocator<char> > const&)
 33666: 0000000009891160    64 OBJECT  GLOBAL DEFAULT   16 vtable for icu_64::ICUServiceFactory
 33668: 0000000008a44500   100 FUNC    GLOBAL DEFAULT   14 criAtomSoundVoice_GetNumFreeVoices
 33756: 0000000008a68d5c   320 FUNC    GLOBAL DEFAULT   14 criNcVoice_End
 33766: 000000000868b7f0   324 FUNC    WEAK   DEFAULT   14 icu_64::ICUBreakIteratorService::ICUBreakIteratorService()
 33802: 000000000a5701c0    88 OBJECT  GLOBAL DEFAULT   23 CriManaSoundAtomVoice::s_cs_list_work
 33858: 0000000008a62e18   116 FUNC    GLOBAL DEFAULT   14 criAtom_SetDeviceReadBitrate_ANDROID
 33937: 0000000008a5cf18    72 FUNC    GLOBAL DEFAULT   14 criAsrVoice_Stop
 34032: 0000000008708920    96 FUNC    GLOBAL DEFAULT   14 icu_64::ChoiceFormat::setChoices(double const*, icu_64::UnicodeString const*, int)
 34034: 000000000855ffb0     8 FUNC    WEAK   DEFAULT   14 physx::Gu::TriangleMesh::getVertices() const
 34040: 00000000089c55c8   124 FUNC    GLOBAL DEFAULT   14 CriManaSoundAtomVoice::Finalize()
 34060: 00000000086d188c    16 FUNC    GLOBAL DEFAULT   14 icu_64::ICUService::reInitializeFactories()
 34061: 0000000008a3dbe0   120 FUNC    GLOBAL DEFAULT   14 criAtomTblVoiceLimitGroup_GetItem
 34128: 00000000082468f4    36 FUNC    GLOBAL DEFAULT   14 std::__ndk1::random_device::~random_device()
 34146: 00000000086cf620   140 FUNC    GLOBAL DEFAULT   14 icu_64::ICUServiceKey::currentDescriptor(icu_64::UnicodeString&) const

## Unreal networking strings
 1213d4 sendto
 1213db recvfrom
 9c0448 ENetworkFailure::OutdatedClient
 9c0468 ENetworkFailure::PendingConnectionFailure
 9c6e44 ${"sendTo":"%s"}
 9d144c GameNetDriver
 9d3703 NetDriver
 9d3888 ENetworkFailure::FailureReceived
 9ed4f7 CsResetUdpSocketEnable
 9ed740 ## [ NTL WARNING ][ %d ] RecvFrom Error [ %s ][ %08x ]
 9fa543 ENetworkFailure::ConnectionTimeout
 9fa566 ENetworkFailure::OutdatedServer
 a0842e SendToBgCppStringInt1
 a0b3d0 PendingNetDriver
 a13403 DcTestPingConnectionTimeoutMs
 a1a84d SendToBgCppStringIntOne
 a1ceb5 EUEOnlineSubSystemImplStep::TERM
 a32258 ActiveNetDrivers
 a45b77 ParticleModuleEventsToSendToGame
 a5612c DemoNetDriver
 a584cb ENetworkFailure::NetDriverAlreadyExists
 a584f3 ENetworkFailure::ConnectionLost
 a5e8c8 CmpNetworkIoCmpConnectionTimeoutMs
 a7228d ChannelDatagramLength
 a915e1 NamedNetDriver
 a97ea2 DcTestConnectionTimeoutMs
 aa4cce ENetworkFailure::NetDriverCreateFailure
 aab670 TurnNetworkIoConnectionTimeoutMs
 aab714 CsResetUdpSocketIntervalMs
 ac9f81 G:/UE4.26_eFB/Base/Engine/Source/Runtime/PacketHandlers/PacketHandler/Private/PacketHandler.cpp
 adbb24 MeshNetDriver
 ae3c69 ConnectionTimeoutUs
 b00fc1 EUEOnlineSubSystemImplStep::INIT
 b00fe2 EUEOnlineSubSystemImplStep
 b14f88 BeaconNetDriver
 b17039 ENetworkFailure::NetDriverListenFailure
 b2b303 SendToConsole
 b43991 NetworkIoConnectionTimeoutUs
 b439ae TurnNetworkIoTcpConnectionTimeoutMs
 b4eb87 G:/UE4.26_eFB/Base/Engine/Source/Runtime/PacketHandlers/PacketHandler/Classes/HandlerComponentFactory.h
 b62809 ENetworkFailure
 b754f6 ENetworkFailure::NetGuidMismatch
 b9c116 NetDriverDefinition
 ba2c99 EstablishedConnectionTimeoutUs
 bad140 EUEOnlineSubSystemImplStep::IDLE
 baf43f NetDriverName
 bc288a /Script/PacketHandler
 bc350c ENetworkFailure::Type
 bc3ee3 ConnectionTimeout
 be8d2a ENetworkFailure::NetChecksumMismatch
 bfb77a EffectorDiffSocket
 bfbfaf NetDriverDefinitions
 c0f2ac G:/UE4.26_eFB/Base/Engine/Source/Runtime/Engine/Classes/Engine/NetDriver.h
 c158f2 CmpNetworkIoConnectionTimeoutMs

## Binary contexts
OFFSET=0x9bd7a1 TERM=STUN
CONTEXT=GetFreeCoinToolTipStr EInfoDirectDestination::EXTRA_TRAINING EInfoDirectDestination::MYCLUB_LEAGUE EInfoDirectDestination::GPSHOP LeagueRatingInfo GetDetailViewFameInfoList GetMenuKind worldStr mainStr ELobbyCreatejoinRoomError::ERR_FAILED_STUNCHECK EMenuRoomDetailElement::PK EMenuRoomDetailElement::CPU_LEVEL m_enableRoomEntryRestriction m_forceProceedRemainTime m_maxSubstitutionCount GetMyRoomUserSide GetRoomKindStr GetSelectableRoomUserSide EMatchPassBalloonStep::MATCH_PASS_BALLOON_STEP_ANIM_HIDE EMatchPassReleaseType::MATCH_PASS_RELEASE_UNLOCK m_headerType m_fPesUserInfo CallbackAnimFinishedMod

OFFSET=0x9c6ee8 TERM=STUN
CONTEXT=## CtxHistory ## PeerCtl ## TransportDump_via_%s_ept_%s ${"appTo":"%s"} ${"sendTo":"%s"} ${"channel":0x%04x} ${"prio":%d} ${"status":"%s"} ${"rtt":[%d,%d,%d]} E_NOSUPPORT E_TURN_ALLOCATION_MISSMATCH E_SKIP UPNP_DISCOVERY_TIMEOUT CHECK_STUN_RTT_TIMEOUT ## HelperStatus ${"sendCnt":%d} %*[^ ] US use_parallel_download is_available_http2 use_network_request MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L5 MATCH_STOP_COUNT_SELF_BUF_EMPTY_MCACTIVE RECEIVE_IDLE_TIME TURN_QUALITY_RECENTLY_RTT_MEAN P2PTURNIO_TURN_RTT_VARIANCE LATENCY_TURN_RESOLVING_NAME_ANY_MAX LATENCY_TURN_RESOLVING_NAME_ANY_VARIANCE SEND_

OFFSET=0x9edab7 TERM=STUN
CONTEXT=_HOP_2_UDP_END_TEST IP_ADDRESS_ICMP_END_TEST MATCH_SETTING_STADIUM_ID TURN_QUALITY_BASESESSION_RTT TURN_SESSION_RTT_MEAN LATENCY_TURN_CONNECT_ANY_MAX CONTROL_STYLE_SETTING DCTEST_MEASUREMENT_PROTOCOL SOCKET_ERRORS \s*konami ], LATENCY_NTL_STUNCHECK_PROCESS LATENCY_MODE_ANNTENA_DISP_MATCHING_RESULT SP_REGULATION CS_RESET_UDP_SOCKET_COUNT ACTUAL_MATCH_HZ_MIN ACTUAL_MATCH_HZ_R_VARIANCE ":[ PesSessionManager enable_client_receipt_acknowledge getIntroductoryPriceAmountMicros getOriginalPriceAmountMicros get receipt product_id_list package_type CrossPlatformPrivilegeCheckTask conn_stats OnSysTmp OnSys

OFFSET=0xa00a89 TERM=STUN
CONTEXT="udn":"%s" NewInternalClient GetNATRSIPStatus %s [ 0x%08x ] SERVER_TIME ## PeerDump ${"peerId":%d} ${"natType":0x%08x} ${"status":"%s"} ${"sign":"%08x%08x%08x%08x"} ${"exSessKey":"%s"} E_ACCES E_UNKOWN_PEER E_DUPPEER UPNP_PROCESS_ABORTED STUN_TEST_ERROR TARGET_PEER /proc/net/route net.hostname enabel_ignore_all_command_error ngword_check_at_command align_progress_ready_timeout_sec IPADDR_PEER MATCH_STOP_COUNT_BUF_EMPTY_BURST_L2_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L4_MCACTIVE IDELAY_BUF_SIZE_FOR_INPUT_DELAY_ RTT_ SELF_AUTOMOVE_COUNT SEND_COMMAND_MUST_NOT_DROP_COUNT_RECV NTL_PEER_STATUS TURN

OFFSET=0xa0a304 TERM=STUN
CONTEXT=tomSelect::SETTINGS_GRAPHICS_CUSTOM_SELECT_DEPTH_OF_FIELD ESettingsGraphicsCustomSelect::SETTINGS_GRAPHICS_CUSTOM_SELECT_AUDIENCE ESettingsGraphicsSelect::SETTINGS_GRAPHICS_SELECT_LOW EMenuSettingsSupportSelect ETipsCategory::TIPS_CATEGORY_STUNNING_SHOT ETipsCategory::TIPS_CATEGORY_MATCHING_65 ETipsCategory::TIPS_CATEGORY_MATCHING_75 ETipsCategory::TIPS_CATEGORY_MATCHING_93 VersionInfoStr ETopModeSelectPopupType::POPUP_TYPE_ADDED_COIN ETopModeSelectTutorialType::TUTORIAL_TYPE_SCOUT ETrainingType::TRAINING_TUTORIAL_START GetFavoritePlayer ESymbolOther::ESYMBOL_OTHER_NATIONAL_AFRICA m_sceneNameList 

OFFSET=0xa1c82d TERM=STUN
CONTEXT=rESportsInfoOnly IsFtueChallengeEvent SetIsNeedRewardDialogForTour outTeamNum EInfoDirectDestination::ASSET_SHOP phasePeriod m_pTargetWidget EMenuLobbyGetRoomInfoResult::MENU_LOBBY_GET_ROOM_INFO_RESULT_FOUND ELobbyJoinRoomError::ERR_FAILED_STUNCHECK ELobbyCreatejoinRoomError::ERR_LIVEDATA_UPDATED ELobbyCreatejoinRoomError::ERR_FAILED_MULTIPLAY_PRIVILEGE EMenuRoomDetailElement::MAX_SUBSTITUTION_NUM EMenuRoomDetailElement::CONDITION_AWAY ERoomSettingsKind ERoomGamePhase::ROOM_GAME_PHASE_EX2ND ERoomEntryRestrictionType::ROOM_ENTRY_RESTRICTION_PASSWORD ERoomMode::PRESET_USER_COMPE EConditionType::COND

OFFSET=0xa4b6d0 TERM=STUN
CONTEXT=yDecoderMaxBufferLength Change endpoint. ( is_request NET_LINK_TYPE_UNKNOWN RESERVED RP_INFO M-POST2 USN < InternalPort UpdatePinhole DeletePinhole {"port":"%d","id":"%s","attr":"%s","http":"%d","soap":"%d","dnr":"%d","znr":"%d"} E_MSGSIZE STUN_TEST_PROGRESS STOP_UDP_HOLE_PUNCHING_ERROR CHECK_STUN_RTT_COMPLETE [ %s:%d ][ %d bytes ] HOST_RELAY is_enable_all_command iOs sa_hud_low IPADDRV6_PEER SESSION_MODE GAME_MODE MATCH_STOP_MAX_ROLLING_COUNT_BUF_EMPTY_IV2_MCACTIVE RECEIVED_INVALID_LENGTH TURN_QUALITY_RTT_EWMA_PENALTY DCTEST_RECOMMENDED_REGION LATENCY_MODE_ANNTENA_CMD_GET_GAMEID RTT_MAX RSSI_ME

OFFSET=0xa4b706 TERM=STUN
CONTEXT=NET_LINK_TYPE_UNKNOWN RESERVED RP_INFO M-POST2 USN < InternalPort UpdatePinhole DeletePinhole {"port":"%d","id":"%s","attr":"%s","http":"%d","soap":"%d","dnr":"%d","znr":"%d"} E_MSGSIZE STUN_TEST_PROGRESS STOP_UDP_HOLE_PUNCHING_ERROR CHECK_STUN_RTT_COMPLETE [ %s:%d ][ %d bytes ] HOST_RELAY is_enable_all_command iOs sa_hud_low IPADDRV6_PEER SESSION_MODE GAME_MODE MATCH_STOP_MAX_ROLLING_COUNT_BUF_EMPTY_IV2_MCACTIVE RECEIVED_INVALID_LENGTH TURN_QUALITY_RTT_EWMA_PENALTY DCTEST_RECOMMENDED_REGION LATENCY_MODE_ANNTENA_CMD_GET_GAMEID RTT_MAX RSSI_MEAN DISPRESION _DWN_ID_ getOrderId getAccountIdentifier

OFFSET=0xaab9c3 TERM=STUN
CONTEXT=UHP_FINALIZE_RET ALLOCATE RT_ACK | |->> [ %s ][ %04x ] %02X%02X%02X%02X EventSubURL NewLastConnectionError RemotePort ## Stun Status ${"rtt:":%d} CLASH E_CACHE_EXIST ALLOC_TURN_PERMISSION_BINDING_COMPLETE START_UDP_HOLE_PUNCHING_ABORTED STUN_PING_TIMEOUT HOST_DIRECT TARGET_CHAOS ED_UHP http://ntl.service.konami.net/ntl/api/GateInfo.php ios Ps4 out_of_play_timeout_sec out_of_play STANDARD_DEVIATION SERVNAMEV6_PEER SELF_AUTOMOVE_COUNT_BURST_L4 MATCH_CONTROL_SESSION_SEND_HEADER_SET_DELTATIME_FAIL_COUNT IP_ADDRESS_HOP_2_UDP_BEGIN_TEST TURN_QUALITY_BASE_RTT LATENCY_TURN_CONNECT_PEER_VARIANCE PING_LE

OFFSET=0xad159a TERM=STUN
CONTEXT=d %s%d REFLECTED_FROM TERM TRANSPORT | |->> [ %s ][ 0x%04x ] MappingTestIA urn:schemas-upnp-org:service:WANIPConnection:1 modelNumber </m:%s> }} ctxType ${"t":%d,"c":"%s","p":%d,"r":"%s","o":%d} ALLOC_TURN_PERMISSION_BINDING_ABORTED PEER_STUN REMOVE recieve_timeout_factor enable_sce_http2_error_reason_no_error_handling IPADDRV6 SEND_COMMAND_DROP_COUNT_BURST_L1_MCACTIVE SELF_AUTOMOVE_COUNT_BURST_L3 IP_ADDRESS_UDP_END_TEST MEMORY_PHYSICAL_PEAK_USED_KiB_ TURN_QUALITY_RTT_EWMA SEND_TO_NET_INFO_MAX_SEND_ATTEMPT_INTERVAL APP_YIELD_STATS_INACTIVITY_TIME_MS BPS_SEND_ RX_LOSS_RATE_MEAN Not Implement <uns

OFFSET=0xafd6be TERM=STUN
CONTEXT=ion RecordParts_9 DistributionParts_9 SetUserInfo G:/PES22HC/Dev-600Series/UProject/PesMobile/Source/PesShared/Game/Menu/League/UCMenuLeagueMainMenuBase.h SelectViewCostumeImg MatchMenuStrikeArenaPageRoomBtnInvite CREATEJOINROOM_ERR_FAILED_STUNCHECK Footer_Action /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickWithPlateTrap.CommandTouchFlickWithPlateTrap_C HeelLift Value_Text GamePlanCustomPitchPlayerBase void AUCMenuUserCompeSpectatePauseWait::CallbackExitAlertCancel() /Game/Assets/ui/Data/Widget/General/Alert/AlertSugorokuResult/AlertSugorokuResult.AlertSugorokuR

OFFSET=0xb55bf4 TERM=STUN
CONTEXT=ries\Source\Shared\pes\Game\Online\OnlineSystem\Multiplay\SessionStrategy\OnlineSystemMultiplaySessionStrategyP2pFullMeshWithTurn.cpp ] RP_JSON_DATA SEQ MappingTestIB FilteringTestII Allocate GetNonce |->> [ %s ][ %d ][ %s ] extra E_OK E_STUN_TEST_ERROR E_MUTEX_INVAL FREE_TURN_CHANNEL_BINDING_ABORTED ro.build.version.release XX 8.8.8.8 match_session_not_connected_timeout_sec SERVNAMEV6 PLATFORM_PEERS NUM_GUESTS_END_MATCH MCDEQUEUEHZ_RATE_ MATCH_STOP_COUNT_BUF_EMPTY TURN_QUALITY_DEGRADATION_RATE TURN_SESSION_RESPONSE_WAITING_TIME TURN_SESSION_RTT_MAX TURN_SESSION_ATTRIBUTE_SOFTWARE P2PTURNIO_RX_L

OFFSET=0xb72c30 TERM=STUN
CONTEXT=ClubPlayerPositionSelect::MENU_MYCLUB_PLAYER_POSITION_SELECT_NONE EMenuMyClubPlayerPositionSelect::MENU_MYCLUB_PLAYER_POSITION_SELECT_CB EMenuMyClubPlayerPositionSelect::MENU_MYCLUB_PLAYER_POSITION_SELECT_LSB EMatchingState::MATCHING_STATE_STUN_CHECK EMatchingState::MATCHING_STATE_SYNC EMatchingState::MATCHING_STATE_FAILED EMatchingOptionPing m_sideInfo HasStadiumAssetThumbnail arg3 GetPresentData GetPresentList IsInUserCompe PadEventRight EKonamiidLinkStatus::LinkCloseWebView EMenuOneTimeCmnType::GDK_CROSSPLATFORM_EVENT PopupOneTimeCmnView WelcomeViewClass EAvatarIconSize::NONE SetBackGroundIcon 

OFFSET=0xb8f50a TERM=STUN
CONTEXT=ent LoadTimeoutMs Sub Allocate retry limit exceeded. (limit = MAPPED_ADDRESS O573_REV urn:schemas-upnp-org:service:WANIPConnection:2 TIMEOUT > controlURL NewInternalPort NewLeaseTime InvokeConnectivity E_AGAIN E_NOTCONN E_UPNP_AF_MISMATCH STUN_TEST_ABORTED STOP_UDP_HOLE_PUNCHING_ABORTED FALLBACK default_interval_ms iOS ps4 enable_detailed_http_error match_command_lack_mobile_timeout_sec IDELAY_ CONGESTION_CONTROL_WINDOW_SIZE_ IDELAY_BUF_FATAL_COND_DETERMN_TIME_MAX MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L2 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L1_MCACTIVE NTL_PEER_KEEPALIVE_COUNT RTO_ SENT_COMMAND_

OFFSET=0xba2fba TERM=STUN
CONTEXT=e":{ NewNATEnabled AddPortMapping {"igd":{"status":"%s","lastError":"%s","uptime":"%d","rsip":"%d","nat":"%d","externalIp":"%s"}} ## [ NTL WARNING ][ %d ] GetPeerStatus Error [ pid %d ][ %s ][ %08x ] StunInfo E_CRITICAL DETECT_NAT_COMPLETE STUN_TEST_COMPLETE ,%s JNIHVoidMethodV ntl_ethernet_portselectpolicy gdk OSVERSION_PEERS SELF_AUTOMOVE_COUNT_BURST_L5 SELF_AUTOMOVE_COUNT_BURST_L1_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L1 RECEIVE_UNKNOWN_ERROR_COUNT MEMORY_VIRTUAL_AVAILABLE_KiB_ P2PTURNIO_TURN_RTT_MEAN P2PTURNIO_RTT_MIN_EVALUATION time, ping_mean, ping_variance, ping_min, ping_max, pes_hz_me

OFFSET=0xbcffde TERM=STUN
CONTEXT=r Callback_RentalPlayer Text_White /Game/Assets/ui/Data/Widget/Match/Screen/PointBonusSelection/PointBonusSelection.PointBonusSelection_C DetailViewInstructionToPlayerPitch Text_Ranking_Value Result_Parts_2 MessageParts JOINROOM_ERR_FAILED_STUNCHECK TouchArea_1 /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_3_CallPressure.CommandTouchFlickAdvanced_3_CallPressure_C Scissors BtnAutoPickPlayers_Off IconAlert Text_Formation StatsListBParts_%d TileViewCustom_Friend player_list Receive_Joint_Before Text_Tooltip_Left Parts_Card_3 CampaignPassPartsDisclaimer Text

OFFSET=0xbdc923 TERM=STUN
CONTEXT=RELIABILITY RP_ENTRY_IDX RP_PEER_STATUS TO XPEERADDR O573_CRD_REQ serviceId NewConnectionStatus errorDescription ## Stun Profile ${"ip":"%s","rap":%d,"nr":%d,"avg":%d,"max":%d,"min":%d} ## EventHistory E_NETUNREACH E_NO_DELEGATE TARGET_STUN_SERVER jp/konami/android/common/IabBroadcastReceiver NODE_ID_PEER RECEIVED_LENGTH MATCH_SETTING_TIMEZONE TURN_QUALITY_DEGRADATION_RTT_COUNT LATENCY_TURN_RESOLVING_NAME_MAX GAME_SERVER_STATS_SEND_URL LATENCY_MODE_ANNTENA APP_YIELD_STATS_ACTIVITY_TIME_MS TRANSPORT_RTT_MEAN receipt_check_retry_count CmdVerifyUserCanBuy CmdSaveReceipt getIconUrl getPriceAmountM

OFFSET=0xbf8d0b TERM=STUN
CONTEXT=led ESettingsSoundSelect::SETTINGS_SOUND_SELECT_AUDIO EKonamiIdStatus::KONAMIID_STATUS_NONE EKonamiIdStatus::KONAMIID_STATUS_SHOW_VIEW EMenuSettingsSupportSelect::MENU_GAME_SETTINGS_SELECT_CONTACT GetBadgeCount ETipsCategory::TIPS_CATEGORY_STUNNING_PASS ETipsCategory::TIPS_CATEGORY_QUICK_GOAL_GIVEUP tipsType EMenuSettingsVisualQuality::MENU_VISUAL_QUALITY_KIND_GRAPHICS_STADIUM GetFlowStr EMenuTopMatchPresetKind::KIND_MATCH_PASS EBannerPanelType EAnnouncementType::ANNOUNCEMENT_TYPE_COMPETITION ETopModeSelectFlow::FLOW_EXTRA_SUPPORT ETopModeSelectFlow::FLOW_PACK_CONTENT_LIST ETopModeSelectSegment::S

OFFSET=0xc02768 TERM=STUN
CONTEXT=":"%s"} ${"%s":"%s"} ${"%s":"%s"} ## UpdateWarning ${"Update:":%d} ${"Recv:":%d} E_TIMEOUT E_BADF ALLOC_TURN_PORT_QUOTA_ERROR REFRESH_TURN_PERMISSION_BINDING_ERROR FREE_TURN_PERMISSION_BINDING_COMPLETE ALLOC_TURN_CHANNEL_BINDING_ABORTED STUN_PING_COMPLETE ntl_portcontext_update NODE_ID SEND_COMMAND_DROP_COUNT_BURST_L4 ACTUAL_MATCH_HZ_ ACCESS_LINE_TEST_COUNT IDELAY_BUF_SIZE_CORRECTION_VALUE_ MATCH_SETTING_SEASON TURN_UDP CS_SERVER_LABEL TURN_IO_SET_SESSION_ERROR LATENCY_MODE_PRE_MENU_CMD_START_GAME V4_TCP_SOCKET_ERROR UE_THREAD_LAST_UPDATED BACKGROUND_NOW Def_System_PESVERSION_FAKE_ENABLE getSku

OFFSET=0x9b9e8d TERM=Stun
CONTEXT=P_MenuRoomSendUserCommentView.BP_MenuRoomSendUserCommentView_C Text_VictoryPoint_Value EventInfo Text_AllGet_Title /Game/Assets/ui/Data/Widget/General/MainMenu/MainMenu_3/MainMenu_3.MainMenu_3_C ActionButtonPauseChoice CommandClassic_Plate_StunningShot_1 Icon_WatchingMatch Text_TotalItem UserCommendation_2 UserStats_2 ANY2_W_753 CONNECTION_REPORT_VIEW TooltipCenter Tooltip_Off Parts_Card_5 Text_Heading_Reward /Game/Assets/ui/Data/Widget/Parts/Icon/CmnIconReward/CmnIconReward.CmnIconReward CampaignPassMapPartsTop SE_CP_MAP_START Img_BG_Wide Img_Bar CampaignPassPointStage_Green_1 CampaignPassPointSt

OFFSET=0xa19610 TERM=Stun
CONTEXT=nline/lobby/RoomSettingMatchSettings/BP_MenuLobbyRoomMatchSettingsSelectView.BP_MenuLobbyRoomMatchSettingsSelectView_C MatchMenuStrikeArenaPagePlayer CallbackAlertResendEmail Slider Plate_Default CommandClassic_Shoot_2 CommandClassic_Plate_StunningShot_2 ButtonLargeText InGameExplanationText FrameBoth DrawOpen void AUCMenuUserCompeSpectatePauseWait::CallbackExitAlertExecute() coop_user_stats CallbackCloseDialog Text_GraphVertical_5 Text_Draw_Item Text_MainReward OnCloseExpiredAlert SugorokuRemainSquare Win SE_CP_MAP_POINT Text_Disclaimer CampaignPassPointStage_Orange_1 CampaignPassPointIcon_Blue_3

OFFSET=0xa2611d TERM=Stun
CONTEXT=tun method. ( Responded stun method. (REFRESH_SUCCESS_RESPONSE) formation_json avator ETHERNET:OK 0.0.0.0 DATA OTHER_ADDRESS RP_P2P_HEADER CHANNEL MappingTestID Connection: Keep-Alive minor <?xml version="1.0"?> NewProtocol AddPinhole ## StunAgentDump isEnabled LOG_ACTIVE UhpFinalize E_HOSTDOWN E_MUTEX_SRCH HTTP_SESSION_ERROR UPNP_DELETE_PORT_FORWARDING_ERROR ALLOC_TURN_PORT_COMPLETE PEER_RELAYED command_auto_retry windows match_sync_failed_timeout_sec NSW ABNORMAL_END_FLAG HOP_COUNT_ICMP_BEGIN_TEST RX_RLOSS_RATE_ SELF_AUTOMOVE_COUNT_BURST_L2_MCACTIVE TURN_QUALITY_BASESESSION_TRANSPORT_RTT TURN_

OFFSET=0xa6577c TERM=Stun
CONTEXT=k_C /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_3_SharpTouch.CommandTouchFlickAdvanced_3_SharpTouch_C /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_3_StunningPass.CommandTouchFlickAdvanced_3_StunningPass_C PartsGraph120 /Game/Assets/ui/Data/Widget/General/Views/ConnectionReportView/ConnectionReportView.ConnectionReportView_C Text_1Spot CampaignPassMapPartsInfoReward_3_3 CampaignPassMapPartsInfo Img_BG_0403 Img_Icon CampaignPassPointGuage_Green_1 CampaignPassPointGuage_Purple_1 CampaignPassPointGuage_Purple_2 

OFFSET=0xa657a5 TERM=Stun
CONTEXT=atchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_3_SharpTouch.CommandTouchFlickAdvanced_3_SharpTouch_C /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_3_StunningPass.CommandTouchFlickAdvanced_3_StunningPass_C PartsGraph120 /Game/Assets/ui/Data/Widget/General/Views/ConnectionReportView/ConnectionReportView.ConnectionReportView_C Text_1Spot CampaignPassMapPartsInfoReward_3_3 CampaignPassMapPartsInfo Img_BG_0403 Img_Icon CampaignPassPointGuage_Green_1 CampaignPassPointGuage_Purple_1 CampaignPassPointGuage_Purple_2 CampaignPassPointIcon_Red_3 CampaignPassP

OFFSET=0xa7234c TERM=Stun
CONTEXT=P2P_ADHOC_BTC DelayBasedLimiterLimitSafetyFactor ChannelDatagramLength ActualMatchHzWithInactiveIntervalUs MatchGageAdjustment MultiplayLlpChangeoverCommandThread ACTIVENETWORK:WIFI jp/konami/android/common/Reachability |->> [ %s ] ${"SendStunMsg":"[ %s ][ %s ] to [ %s:%d ][ %d bytes ]","tid":"%08x%08x%08x","act":"%s"} O573_FREE_CHANNEL MappingTestIC MappingTestII MappingTestIV 239.255.255.250 {"sts":[ {"st":"%s","status":"%s","resp":"%d","loc":"%s","uuid":"%s","srv":"%s"} ${"ctx":[%d,%d,%d,"%s",%d,%d,%d,%d]} nan E_MUTEX_BUSY %li nn_manual_blocklist_update SEND_COMMAND_DROP_COUNT_BURST_L2 SELF_A

OFFSET=0xa78229 TERM=Stun
CONTEXT=gStyle SelectViewTargetPlayerBtnRight List1LineBtnInfo Parts_OffenseDefense RecordParts_5 OnClosedOperationExtra Page_Room LOBBY_CREATEJOINROOM_ERR_FAILED_MULTIPLAY_PRIVILEGE ERR_OTHER_PLATFORM_USER_IN_ROOM Text_Defence TouchArea_5 Command_StunningShot /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_2_KickAngle_GoalKick.CommandTouchFlickAdvanced_2_KickAngle_GoalKick_C /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_0_FinesseDribble.CommandTouchFlickAdvanced_0_FinesseDribble_C /Game/Assets/ui/Data/Widget/General/Mat

OFFSET=0xa8b6d8 TERM=Stun
CONTEXT=idget/Mode/StrikeArena/SelectViewStrikeArenaPlayer/SelectViewStrikeArenaPlayer.SelectViewStrikeArenaPlayer_C SetTeamID JOINROOM_ERR_FAILED_PLATFORMSESSION_NOT_PERMITED LOBBY_JOINROOM_ERR_FAILED_MULTIPLAY_PRIVILEGE CommandClassic_Plate_Pass_Stunning_1 ButtonSmallText_1 /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_1_Sliding.CommandTouchFlickAdvanced_1_Sliding_C /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_1_Clear.CommandTouchFlickAdvanced_1_Clear_C Text_Point_Item Text_GraphVertical_1 OnCloseAlertForFailedProce

OFFSET=0xaab94e TERM=Stun
CONTEXT=MatchCommand Unknown state. (status = Allocation mismatch. (error code = CMD_ALIGN_PROGRESS wait_other RP_NAT_TYPE UHP_FINALIZE_RET ALLOCATE RT_ACK | |->> [ %s ][ %04x ] %02X%02X%02X%02X EventSubURL NewLastConnectionError RemotePort ## Stun Status ${"rtt:":%d} CLASH E_CACHE_EXIST ALLOC_TURN_PERMISSION_BINDING_COMPLETE START_UDP_HOLE_PUNCHING_ABORTED STUN_PING_TIMEOUT HOST_DIRECT TARGET_CHAOS ED_UHP http://ntl.service.konami.net/ntl/api/GateInfo.php ios Ps4 out_of_play_timeout_sec out_of_play STANDARD_DEVIATION SERVNAMEV6_PEER SELF_AUTOMOVE_COUNT_BURST_L4 MATCH_CONTROL_SESSION_SEND_HEADER_SET_

OFFSET=0xac470e TERM=Stun
CONTEXT=te InstructionToPlayerIcon match_role_setting InfoRecord RecordParts_7 DistributionParts_8 Text_Item_Value MatchMenuStrikeArenaBtnChangePlayer ERR_PLATFORM_SESSION_ID_MISMATCH AttackDefenceLevel_4 CommandClassic_Pass_3 CommandClassic_Plate_Stunning_Diffense_2 CommandClassic_Plate_Cross_1 /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_3_KickFeint.CommandTouchFlickAdvanced_3_KickFeint_C SetAlert tutorialMain operation_guide Text_GraphHorizontal_5 PartsGraph90 evaluation Text_Loss_Bonus Tooltip_Left CallbackCloseRewardView Receive_First_Before Text_Nation_Le

OFFSET=0xaf95d1 TERM=Stun
CONTEXT=key update TWCR Exhibition/ProcessPostMatchPreview Match/Sugoroku/SugorokuInfoStart Intro/ProcessIntroInGameTextLoad Online/Match/MatchProcessStartupGame Online/EvCompe/TourPvp/ProcEvCompeEventEnter confirmCountry squares_present_list LobbyStunCheckAfterMatch redCard ExecuteConsoleCommand "gc.MaxObjectsNotConsideredByGC 1" ExecuteConsoleCommand "gc.MaxObjectsInGame 0" new SaveWaitDialog SU_10 SA_C_NMB_E18 SA_C_NMB_E19 SA_C_NMB_E78 SA_C_NMB29 SA_C_NMB70 SA_C_NMB88 SA_C_NMB98 version=" A1_PZA AdditionalParts CheckUniqueMotionBegin CheckPosession CheckOnotherSideShortTimeLast2Touch CheckMatchStatisti

OFFSET=0xb10ed2 TERM=Stun
CONTEXT=ur/BP_MenuCmnViewEventPoint.BP_MenuCmnViewEventPoint_C ERR_BLOCK_ROOM_USER AttackDefenceLevel_2 CommandClassic_Shoot_3 CommandClassic_Plate_Shoot_2 /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_3_StunningShot.CommandTouchFlickAdvanced_3_StunningShot_C CallbackCloseView Text_Commendation Text_GraphHorizontal_1 Choice_Base CampaignPassMapPartsDetail SMenuCampaignPassMapBoxChoiceLayer CampaignPassPointBase_Orange_1 CampaignPassPointBase_Orange_2 CampaignPassPointBase_Red_2 CampaignPassPointStage_Red_3 CampaignPassPointGuage_Blue_3 CampaignPassPointGuage_Gre

OFFSET=0xb10efb TERM=Stun
CONTEXT=wEventPoint_C ERR_BLOCK_ROOM_USER AttackDefenceLevel_2 CommandClassic_Shoot_3 CommandClassic_Plate_Shoot_2 /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_3_StunningShot.CommandTouchFlickAdvanced_3_StunningShot_C CallbackCloseView Text_Commendation Text_GraphHorizontal_1 Choice_Base CampaignPassMapPartsDetail SMenuCampaignPassMapBoxChoiceLayer CampaignPassPointBase_Orange_1 CampaignPassPointBase_Orange_2 CampaignPassPointBase_Red_2 CampaignPassPointStage_Red_3 CampaignPassPointGuage_Blue_3 CampaignPassPointGuage_Green_3 LoopEffectAnim OnEndReceiveShopPoint

OFFSET=0xb49612 TERM=Stun
CONTEXT=gnRankingBase.h GameLevel_Off InfoMission Callback_BeforeMatchAlert uiEmblem_Away_Black uiEmblem_Black_6 Icon_MatchHistory SE_EVENT_BONUS_SELECT Result_Parts_3 ChatText AttackDefenceLevel_5 CommandClassic_Plate_Shoot_1 CommandClassic_Plate_Stunning_Diffense_3 /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_0_DashDribble.CommandTouchFlickAdvanced_0_DashDribble_C /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_2_FreeKick.CommandTouchFlickAdvanced_2_FreeKick_C plan Layout_Stats skipped_demo_after_pk /Game/Assets/ui/Da

OFFSET=0xb5c6eb TERM=Stun
CONTEXT=D_CONNECT_RELAY /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_0_Pass.CommandTouchFlickAdvanced_0_Pass_C /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_3_StunningCross.CommandTouchFlickAdvanced_3_StunningCross_C Switch_OpponentInfo IconCaptain TooltipLeft SugorokuGoalReward Img_Base_Bonus Parts_Flag_6 Parts_Flag_7 Parts_Flag_9 Text_Total_Value_After G:/PES22HC/Dev-600Series/UProject/PesMobile/Source/PesShared/Game/Menu/MatchPass/MapType/UMenuCampaignPassMapBoxChoiceLayer.cpp CampaignPassPointBase_Green_2 Campaign

OFFSET=0xb5c715 TERM=Stun
CONTEXT=t/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_0_Pass.CommandTouchFlickAdvanced_0_Pass_C /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_3_StunningCross.CommandTouchFlickAdvanced_3_StunningCross_C Switch_OpponentInfo IconCaptain TooltipLeft SugorokuGoalReward Img_Base_Bonus Parts_Flag_6 Parts_Flag_7 Parts_Flag_9 Text_Total_Value_After G:/PES22HC/Dev-600Series/UProject/PesMobile/Source/PesShared/Game/Menu/MatchPass/MapType/UMenuCampaignPassMapBoxChoiceLayer.cpp CampaignPassPointBase_Green_2 CampaignPassPointGuage_Orange_2 CampaignPassPointG

OFFSET=0xb82dbf TERM=Stun
CONTEXT=electViewTargetPlayerBtnRightNext State_None SetCancelBtnCallback CoopUserInfo MatchMenuStrikeArenaPageRewardCell_1 TileViewCustom_Tournament CallbackAlertCancel Date_Off ActionButtonSpectatePause Text_TrapThrough CommandClassic_Plate_Pass_Stunning_2 StepOver Text_GraphHorizontal_3 team_record CallbackCloseAlertSAPlayer CallbackShowAnimFinished Alignment_Left Parts_Card_7 uiNation_Effect OnReceiveAnimFinished G:/PES22HC/Dev-600Series/UProject/PesMobile/Source/PesShared/Game/Menu/MatchPass/MenuType/UCMenuCampaignPassMenuTypeCtrlBase.h CampaignPassPointBase_Pink_1 CampaignPassPointBase_Purple_1 Camp

OFFSET=0xba2f92 TERM=Stun
CONTEXT= [ %s ] WANPPPConnection SCPDURL {"device":{ NewNATEnabled AddPortMapping {"igd":{"status":"%s","lastError":"%s","uptime":"%d","rsip":"%d","nat":"%d","externalIp":"%s"}} ## [ NTL WARNING ][ %d ] GetPeerStatus Error [ pid %d ][ %s ][ %08x ] StunInfo E_CRITICAL DETECT_NAT_COMPLETE STUN_TEST_COMPLETE ,%s JNIHVoidMethodV ntl_ethernet_portselectpolicy gdk OSVERSION_PEERS SELF_AUTOMOVE_COUNT_BURST_L5 SELF_AUTOMOVE_COUNT_BURST_L1_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L1 RECEIVE_UNKNOWN_ERROR_COUNT MEMORY_VIRTUAL_AVAILABLE_KiB_ P2PTURNIO_TURN_RTT_MEAN P2PTURNIO_RTT_MIN_EVALUATION time, ping_mean, ping

OFFSET=0xbdc8a8 TERM=Stun
CONTEXT=t NoMoveOperationCheckerKind Responded stun method. (CHANNEL_BIND_ERROR_RESPONSE) json_data side_list PUNCHING_FINISHED RP_RELIABILITY RP_ENTRY_IDX RP_PEER_STATUS TO XPEERADDR O573_CRD_REQ serviceId NewConnectionStatus errorDescription ## Stun Profile ${"ip":"%s","rap":%d,"nr":%d,"avg":%d,"max":%d,"min":%d} ## EventHistory E_NETUNREACH E_NO_DELEGATE TARGET_STUN_SERVER jp/konami/android/common/IabBroadcastReceiver NODE_ID_PEER RECEIVED_LENGTH MATCH_SETTING_TIMEZONE TURN_QUALITY_DEGRADATION_RTT_COUNT LATENCY_TURN_RESOLVING_NAME_MAX GAME_SERVER_STATS_SEND_URL LATENCY_MODE_ANNTENA APP_YIELD_STATS_

OFFSET=0xbf5fbf TERM=Stun
CONTEXT=m SetData SelectViewCostumeBtnRight Name_User MainRewardParts Text_Bonus_Item MatchMenuStrikeArenaPageRoom CREATEJOINROOM_ERR_FAILED_CONNECT_RELAY_TIMEOUT ERR_BLOCKED_ROOM_USER Text_Url CommandClassic_Plate_Feint_Smart CommandClassic_Plate_Stunning_Diffense_1 MatchMainMenuIcon SetColor1 Text_GraphHorizontal_6 highlight Alignment_Right Parts_Flag_5 Parts_Flag_11 CampaignPassMapScrollSmall CamPassPackControlWaitTag void UCItemCampaignPassPoint::CallbackFinishedAfterMatch50To100() /Game/Assets/ui/Data/Widget/Objective/Screen/CampaignPassPoint_Tex/Tex1080/ AlertCampaignPoint_Plate_Purple_3 Stage_%d Ca

OFFSET=0xc15a50 TERM=Stun
CONTEXT=ccessLineTesterFakeDataLength NetworkTesterCheckDegradationEnable ObservePlaybackMatchActiveStatusCheckTimeMs DefaultPps FecQueueMediaSpecificEnable MatchRecvCallRecvPossibleEnable is_finish chatNo CMD_PLATFORM_SESSION REQUEST_PUNCHING RecvStunMsg FF0E::C NewEnabled GetExternalIPAddress {"mappingList":{ ## AllocTurnPort Endpoint NotFound. ## MISC ${"Seed":%02x%02x%02x%02x%02x%02x} ${"Abort":%08x} ALLOC_PERM E_ADD_PORT_MAPPING_ERROR START_UDP_HOLE_PUNCHING_ERROR KEEPALIVE PEER_HOST pes_thread_onsys_manager total_timeout IOS android ps5 XBX onmode NATTYPE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L3_MCACT

OFFSET=0x9c6d2c TERM=stun
CONTEXT=toEstimatorRttEwmaDeviationSafetyCoefficient FecQueueMediaSpecificRedundancy ActualMatchHzWithInactiveFatalConditionHzThreshold FrameRecoveryEnable Ignored the received data. (recvCallback is not set) Unauthorized. (error code = Requested stun method. (CHANNEL_BIND_REQUEST) platform_user_name USERNAME RP_RELAYED_ADDRESS UHP_FINALIZE FilteringTestI RefreshPermission UhpFinalizeHandler Content-Type: text/xml; charset="utf-8" FOUND titleCode ## CtxHistory ## PeerCtl ## TransportDump_via_%s_ept_%s ${"appTo":"%s"} ${"sendTo":"%s"} ${"channel":0x%04x} ${"prio":%d} ${"status":"%s"} ${"rtt":[%d,%d,%d

OFFSET=0x9da594 TERM=stun
CONTEXT=High UERHIThreadAffinityMask ListenerWorkerCriticalDelayThreshold Network DscpEnable TurnNetworkIoPingIntervalMs DcTestForClientServerModeRecommendedRegionMode AccessLineTesterTimeoutTimeMs Session UseTickForIndicatorDisplay -> Requested stun method. (REFRESH_REQUEST) O573_CR_REQ |->> [ %s ][ %d bytes ] urn:schemas-upnp-org:service:WANPPPConnection:1 urn:schemas-upnp-org:service:WANIPv6FirewallControl:1 FF05::C friendlyName "serviceType":"%s","serviceId":"%s","controlUrl":"%s","eventSubUrl":"%s","scpdUrl":"%s" FORMALLY_CONNECTED E_NOCHILD DETECT_NAT_ABORTED FREE_TURN_CHANNEL_BINDING_COMPLETE [

OFFSET=0x9ed68d TERM=stun
CONTEXT=atorSendQueueSize MaxPps ChannelSendQueueRtoSummaryStatisticsWindowSize FecQueueMediaSpecificEncoderMaxBufferLength ActualMatchHzWithInactiveFatalConditionDeterminationTimeUs ForceSetMatchCommandHz SuspendTimeoutMs Unknown error. Responded stun method. (ALLOCATE_SUCCESS_RESPONSE) FINGERPRINT REQUEST RP_APPROVAL RP_SYNC User-Agent: Mozilla/4.0 (compatible; UPnP/1.0; KONAMI) # [ WARNING ] FakeKeepAlive Switch Enaled. ## [ NTL WARNING ][ %d ] RecvFrom Error [ %s ][ %08x ] ## LastAnalyseTransport ${"CheckPktSize:":%d} ${"AllowRttPeakMsec:":%d} ${"AllowRttAvgMsec:":%d} ${"SamplingNr:":%d} ${"TimeoutMs

OFFSET=0xa2602c TERM=stun
CONTEXT=dgementTimeMs FecQueueParityEncoderEnablePadding ActualMatchHzFatalConditionHzThreshold NoMoveOperationCheckerKindForStrikeArena IsEnabledDisplayingLinesmanAndRefereeOnMobile unique_lock::lock: already locked ktc-0.0.0 Responded unexpected stun method. ( Responded stun method. (REFRESH_SUCCESS_RESPONSE) formation_json avator ETHERNET:OK 0.0.0.0 DATA OTHER_ADDRESS RP_P2P_HEADER CHANNEL MappingTestID Connection: Keep-Alive minor <?xml version="1.0"?> NewProtocol AddPinhole ## StunAgentDump isEnabled LOG_ACTIVE UhpFinalize E_HOSTDOWN E_MUTEX_SRCH HTTP_SESSION_ERROR UPNP_DELETE_PORT_FORWARDING_ERROR

OFFSET=0xa26045 TERM=stun
CONTEXT=ityEncoderEnablePadding ActualMatchHzFatalConditionHzThreshold NoMoveOperationCheckerKindForStrikeArena IsEnabledDisplayingLinesmanAndRefereeOnMobile unique_lock::lock: already locked ktc-0.0.0 Responded unexpected stun method. ( Responded stun method. (REFRESH_SUCCESS_RESPONSE) formation_json avator ETHERNET:OK 0.0.0.0 DATA OTHER_ADDRESS RP_P2P_HEADER CHANNEL MappingTestID Connection: Keep-Alive minor <?xml version="1.0"?> NewProtocol AddPinhole ## StunAgentDump isEnabled LOG_ACTIVE UhpFinalize E_HOSTDOWN E_MUTEX_SRCH HTTP_SESSION_ERROR UPNP_DELETE_PORT_FORWARDING_ERROR ALLOC_TURN_PORT_COMPLETE

OFFSET=0xaab1fc TERM=stun
CONTEXT=ENU_INFO is_first use_ranking ml_event_info CMD_GET_MATCHING_RESULT can_input_redeem_code CmdGetRanking.php command_connect_timeout_sec login_bonus_bg_image_name_list short_demo_limit_online use_league_category CMD_GET_VSCOM_GAME_RESULT is_stun_keep_alive_failed is_background_timeout ex_flag defense_positioning AGENT CmdRequestUserDelete.php CmdSendRecruitCode.php CMD_SEND_REPORT gamerelay_list setplay_fk_long market_value auto_offsidetrap bring_uniform div uniform_list_home CMD_GET_EVENT_SELF_RECORD difference_squad_data is_out_of_countries CmdSendMlEventProceed.php CmdSendFriendRequest.php enabl

OFFSET=0xbb6883 TERM=stun
CONTEXT=m DelayBasedLimiterEnable MaxSegmentSize ActualMatchHzFatalConditionDeterminationTimeUs ForceSetMatchCommandHzLowLimit G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineSystem\Multiplay\OnlineSystemMultiplaySession.cpp Responded stun method. (REFRESH_ERROR_RESPONSE) Failed to update request refresh. np_match_id np_account_id tacticsPlan_kind RESPONSE_PORT SOFTWARE RP_REFLEXIVE_ADDRESS | |->> [ %s ][ %s ] | |->> [ %s ][ %d byte ] CREATEPERMISSION KeepAlive FreeChannel eventSubURL "upnpVersion":"" NewExternalIPAddress <%s>%s</%s> <%s>%d</%s> # [ WARNING ] EventHandler IS NULL. ABORTED u

OFFSET=0xbc9bb8 TERM=stun
CONTEXT=ameResolverTimeoutMs TurnNetworkIoQuickPingIntervalMs DcTestEraseUdpStickyFailure DcTestVersion AccessLineTesterMaxTtl P2P_ADHOC_BLE_GIVE_UP_QUICKLY_LEVEL FastTcpAlpha FastTcpGamma ChannelSchedulerPriority Update connection ID. ( Responded stun method. (ALLOCATE_ERROR_RESPONSE) ACTIVENETWORK:CELLULAR RETRY_PUNCHING ::%s0 BINDING RP_ENTRY MappingTestIG ${"%s":"[ %s ][ %s ] from [ %s ][ %d bytes ]","tid":"%08x%08x%08x"} md5 Cache-Control: no-cache Pragma: no-cache deviceType DeviceProtection ServerTime reflexiveAddrStr DETECT_NAT_ERROR ## CoreStatus ${"sendCnt":%d} ALEART wait_error_handling defau

OFFSET=0xbc9e58 TERM=stun
CONTEXT=check_on_resume SEND_COMMAND_DROP_COUNT_BURST_L5_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_MCACTIVE SENT_VOICE_DATA_LENGTH MATCH_ID ISCHEAT SOC_MANUFACTURER LATENCY_MODE_ANNTENA_CMD_SET_GAME_SESSION_CHECK_RES IDELAY_MAX_MCACTIVE RSSI_R_MAX pesam.stun.service.konami.net Test Invalid Receipt getName ()Ljava/util/List; getOfferTags need_kgs_purchase_unlock Wi multi_stats_wait_upload_flag accept_background_times grpc.expand_wildcard_addrs grpc.disable_client_authority_filter g_glip && "gRPC library not initialized. See " "grpc::internal::GrpcLibraryInitializer." G:/PES22HC/Dev-600Series/Source/Shared/basic/

OFFSET=0xbdc7df TERM=stun
CONTEXT=nputDelayWirelessWeight WebSocketClientConnectRetryCount AccessLineTesterNetworkQualityPoorThreshold NetworkTesterInitializeTimeoutMs SendOutHeaderOverheadLength DelayBasedDetectionSrttSmoothCoefficient NoMoveOperationCheckerKind Responded stun method. (CHANNEL_BIND_ERROR_RESPONSE) json_data side_list PUNCHING_FINISHED RP_RELIABILITY RP_ENTRY_IDX RP_PEER_STATUS TO XPEERADDR O573_CRD_REQ serviceId NewConnectionStatus errorDescription ## Stun Profile ${"ip":"%s","rap":%d,"nr":%d,"avg":%d,"max":%d,"min":%d} ## EventHistory E_NETUNREACH E_NO_DELEGATE TARGET_STUN_SERVER jp/konami/android/common/Iab

OFFSET=0xbef464 TERM=stun
CONTEXT=P_ADHOC_WIFIDIRECTLAN P2P_ADHOC_BTC_GIVE_UP_QUICKLY_LEVEL P2P_ADHOC_BLE DelayBasedLimiterHeavyCongestionFactor SlowdownDetectionInFastForwardEnable MatchCommandBufferingControlType InitializationTimeoutMs Closed. (ConnectionId = Requested stun method. (ALLOCATE_REQUEST) member_change_json matchplan_settings_json CELLULAR:OK NTL history PermissionData ERROR_CODE XOR_RELAYED_ADDRESS O573_CR_XADDR SEND UHP_CONNECT ST UDN NewLeaseDuration ${"%s":%08x} CoreNatTypeUpdate {"titleCode":"%s","locale":"%s","version":"%s","extra":"%s","apiLevel":"%d"} INIT ACCEPTABLE E_NOIMPL E_SOAP_METHOD_NOSUPPORT UPNP_DI

OFFSET=0xc0253e TERM=stun
CONTEXT=workIoDegradedByLatencyEnable ConnectMainWaitTimeMS DcTestRecvTimeoutMs NetworkQualityIndicatorUpdateIntervalMs WebSocketClientDisableVerifyPeer NetworkTesterBaseRttMeasurementTimeMs RttSummaryStatisticsWindowSize ProtocolChannel Responded stun method. (CHANNEL_BIND_SUCCESS_RESPONSE) The username and/or password are not set. guest_list getCurrentNetworkInfo RESERVATION_TOKEN MappingTestIE RecvHandler sha256 M-POST <m:%s xmlns:m="%s"> NewUptime NewPortMappingDescription DeletePortMapping UDP ## NetworkInfo ${"%s":[%d,%d,%d,%d]} ${"%s":0x%08x} ${"%s":"%s"} ${"%s":"%s"} ${"%s":"%s"} ## UpdateWarni

OFFSET=0x9c3b00 TERM=TURN
CONTEXT=loop_1_1_mid_michael avoidslide_0_4_000_push_aside_act068_01 feintrun_bodyfake_front_3_3_000_y0_ver03_v2 autoMove_00_dribble_bodyangle_00_180_00_1_1_STEP_near_gabriel ballTouch_04_4_dribble_player_move_0_3_135_y0_gabriel nearDefense_04_BODYTURN_Slant_1_1_frontback_reverse_STEP_near_gabriel nearDribble_03_3_dribble_slide_long_0_0_000_to_180_y0_gabriel nearDribble_04_1_dribble_burst_0_4_090_y0_oriul nearDribble_04_1_dribble_burst_1_4_f090_y0_oriul dm_goal_reactionHigh_got_0002 gkcatchslideback_f01_3_0_y06_135 tacklefoot_parallel_near_2_0_f045_act095 dml_goal_celebrate_0002 dm_oop_ballcome_000_idle_0

OFFSET=0x9c451c TERM=TURN
CONTEXT=_praise_2_3_180_atf090_act064_02 LongVersion_201123_F030_t02_act068_01 enum_dummy401 enum_dummy426 enum_dummy439 autoMove_07_01_gkmovenear_Sidestep_Angle5_3_3 autoMove_08_01_gkmovenear_Sidestep_Angle5_2_2 NEARKEEPER_04_04_gkmovemid_1_1_BODYTURN_SLANT enum_dummy492 enum_dummy580 enum_dummy605 ShortVersion_201123_F011_t02_act068_01 defenseMove_01_parallel_4_0_180_neardelay_act068 gkrise_sidewaysdown_l_0_0_000 cpk_dat/common/anime/FHSequence/bin/Sequenceinfo.bin handR base_g_head_kutiake dml_song_watch ef23_pain_mouth_open ef23_shout_smile_mouth_open_shut ef23_smile_mouth_open_shut neut_Loud_around_m

OFFSET=0x9c6eaa TERM=TURN
CONTEXT=ndler Content-Type: text/xml; charset="utf-8" FOUND titleCode ## CtxHistory ## PeerCtl ## TransportDump_via_%s_ept_%s ${"appTo":"%s"} ${"sendTo":"%s"} ${"channel":0x%04x} ${"prio":%d} ${"status":"%s"} ${"rtt":[%d,%d,%d]} E_NOSUPPORT E_TURN_ALLOCATION_MISSMATCH E_SKIP UPNP_DISCOVERY_TIMEOUT CHECK_STUN_RTT_TIMEOUT ## HelperStatus ${"sendCnt":%d} %*[^ ] US use_parallel_download is_available_http2 use_network_request MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L5 MATCH_STOP_COUNT_SELF_BUF_EMPTY_MCACTIVE RECEIVE_IDLE_TIME TURN_QUALITY_RECENTLY_RTT_MEAN P2PTURNIO_TURN_RTT_VARIANCE LATENCY_TURN_RESOLVI

OFFSET=0x9c6fc7 TERM=TURN
CONTEXT=RY_TIMEOUT CHECK_STUN_RTT_TIMEOUT ## HelperStatus ${"sendCnt":%d} %*[^ ] US use_parallel_download is_available_http2 use_network_request MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L5 MATCH_STOP_COUNT_SELF_BUF_EMPTY_MCACTIVE RECEIVE_IDLE_TIME TURN_QUALITY_RECENTLY_RTT_MEAN P2PTURNIO_TURN_RTT_VARIANCE LATENCY_TURN_RESOLVING_NAME_ANY_MAX LATENCY_TURN_RESOLVING_NAME_ANY_VARIANCE SEND_TO_NET_INFO_SEND_ERROR_COUNT DCTEST_ERROR_VALUE ABNORMALEND_REASON MODELNAME FPS_SETTING GAME_SERVER_STATS_SEND_ LATENCY_MODE_CONNECT_REVISION_CHECK MEMPEAK_MATCH_STEP IS_STAFF SURVEY_ID_2 %lu receipt_check_retry_interval_m

OFFSET=0x9c6fe9 TERM=TURN
CONTEXT= ## HelperStatus ${"sendCnt":%d} %*[^ ] US use_parallel_download is_available_http2 use_network_request MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L5 MATCH_STOP_COUNT_SELF_BUF_EMPTY_MCACTIVE RECEIVE_IDLE_TIME TURN_QUALITY_RECENTLY_RTT_MEAN P2PTURNIO_TURN_RTT_VARIANCE LATENCY_TURN_RESOLVING_NAME_ANY_MAX LATENCY_TURN_RESOLVING_NAME_ANY_VARIANCE SEND_TO_NET_INFO_SEND_ERROR_COUNT DCTEST_ERROR_VALUE ABNORMALEND_REASON MODELNAME FPS_SETTING GAME_SERVER_STATS_SEND_ LATENCY_MODE_CONNECT_REVISION_CHECK MEMPEAK_MATCH_STEP IS_STAFF SURVEY_ID_2 %lu receipt_check_retry_interval_msec getTitle getProductId getOneTi

OFFSET=0x9c6ff0 TERM=TURN
CONTEXT=perStatus ${"sendCnt":%d} %*[^ ] US use_parallel_download is_available_http2 use_network_request MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L5 MATCH_STOP_COUNT_SELF_BUF_EMPTY_MCACTIVE RECEIVE_IDLE_TIME TURN_QUALITY_RECENTLY_RTT_MEAN P2PTURNIO_TURN_RTT_VARIANCE LATENCY_TURN_RESOLVING_NAME_ANY_MAX LATENCY_TURN_RESOLVING_NAME_ANY_VARIANCE SEND_TO_NET_INFO_SEND_ERROR_COUNT DCTEST_ERROR_VALUE ABNORMALEND_REASON MODELNAME FPS_SETTING GAME_SERVER_STATS_SEND_ LATENCY_MODE_CONNECT_REVISION_CHECK MEMPEAK_MATCH_STEP IS_STAFF SURVEY_ID_2 %lu receipt_check_retry_interval_msec getTitle getProductId getOneTimePurch

OFFSET=0x9c700a TERM=TURN
CONTEXT= %*[^ ] US use_parallel_download is_available_http2 use_network_request MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L5 MATCH_STOP_COUNT_SELF_BUF_EMPTY_MCACTIVE RECEIVE_IDLE_TIME TURN_QUALITY_RECENTLY_RTT_MEAN P2PTURNIO_TURN_RTT_VARIANCE LATENCY_TURN_RESOLVING_NAME_ANY_MAX LATENCY_TURN_RESOLVING_NAME_ANY_VARIANCE SEND_TO_NET_INFO_SEND_ERROR_COUNT DCTEST_ERROR_VALUE ABNORMALEND_REASON MODELNAME FPS_SETTING GAME_SERVER_STATS_SEND_ LATENCY_MODE_CONNECT_REVISION_CHECK MEMPEAK_MATCH_STEP IS_STAFF SURVEY_ID_2 %lu receipt_check_retry_interval_msec getTitle getProductId getOneTimePurchaseOfferDetails is_purchas

OFFSET=0x9c702e TERM=TURN
CONTEXT=_available_http2 use_network_request MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L5 MATCH_STOP_COUNT_SELF_BUF_EMPTY_MCACTIVE RECEIVE_IDLE_TIME TURN_QUALITY_RECENTLY_RTT_MEAN P2PTURNIO_TURN_RTT_VARIANCE LATENCY_TURN_RESOLVING_NAME_ANY_MAX LATENCY_TURN_RESOLVING_NAME_ANY_VARIANCE SEND_TO_NET_INFO_SEND_ERROR_COUNT DCTEST_ERROR_VALUE ABNORMALEND_REASON MODELNAME FPS_SETTING GAME_SERVER_STATS_SEND_ LATENCY_MODE_CONNECT_REVISION_CHECK MEMPEAK_MATCH_STEP IS_STAFF SURVEY_ID_2 %lu receipt_check_retry_interval_msec getTitle getProductId getOneTimePurchaseOfferDetails is_purchasable origin CmdWatchInvitation.php 1

OFFSET=0x9cf478 TERM=TURN
CONTEXT=::No4th EMenuCommonResult::Num EDataLinkageResult::DATA_LINKAGE_RESULT_CMD_ERROR EDataTransitionResult::DATA_TRANSITION_NOT_ENOUGH_OS_VER EDataTransitionResult StartAccountTrans EMenuEulaAgreeEndStep::IDLE EMenuEulaSelectListEvent::EVENT_RETURN DecideArea SetMenuTrackrecordOpEventlistDetailViewPVE EMenuEvCompeChallengeSelectState::CheckFirstAlert EMenuEvCompeCpuLevelSelectViewEntryState::Finished reward EMenuEvCompeRankingListType::THIRD EMenuEvCompeEventListBeforeProceedStep::Init EMenuEvCompeMainMenuState::CheckPromotionAcquiredAlert GetMatchSettingInfo SetFlagSwitchToWinLossDisp EEventSettingsS

OFFSET=0x9d024d TERM=TURN
CONTEXT=DE UpdateDL EMenuSettingsSupportSelect::MENU_GAME_SETTINGS_SELECT_USER_DELETE isLogin ETipsCategory::TIPS_CATEGORY_SUGOROKU_PARKOUR_4 ETipsCategory::TIPS_CATEGORY_MATCHING_84 itemStr GetQualityKindList ETopModeSelectPopupType::POPUP_TYPE_RETURN_COIN ETopModeSelectPopupType::POPUP_TYPE_CAMPAIGN_PASS_POINT_ALERT ETopModeSelectTutorialType EBannerPanelType::BANNER_PANEL_TYPE_PACK ETopModeSelectFlow::FLOW_BEGINNER_MISSION ETopModeSelectFlow::FLOW_PRESENT_LIST ETopModeSelectFlow::FLOW_PLAYER_LIST ETopModeSelectFlow::FLOW_PLAY_ENV_SETTINGS ETopModeSelectSegment::SEGMENT_SHOP ETrainingType::TRAINING_FREE

OFFSET=0x9d76b8 TERM=TURN
CONTEXT=_dummy368 LongVersion_201123_F030_t02_act068_02 LongVersion_201124_F031_t01_act068_06 enum_dummy387 enum_dummy390 autoMove_03_01_gkmovenear_Sidestep_Angle5_1_1 autoMove_06_01_gkmovemid_Sidestep_Angle5_1_1 NEARKEEPER_04_04_gkmovemid_2_2_BODYTURN_SLANT NEARKEEPER_04_04_gkmovenear_1_1_BODYTURN_SLANT autoMove_11_bodyangle_rolling_slow_3_3_Front_to_Back_mid_michael enum_dummy483 enum_dummy536 enum_dummy564 enum_dummy592 enum_dummy618 enum_dummy623 enum_dummy648 defenseMove_01_parallel_4_3_neardelayback_act068_02 passGetMove_01_run_3_3_f180_act001 .geom angry_shout_M_01 angry_talk_S_02 base_d_end_cup_sh

OFFSET=0x9d76e7 TERM=TURN
CONTEXT= LongVersion_201124_F031_t01_act068_06 enum_dummy387 enum_dummy390 autoMove_03_01_gkmovenear_Sidestep_Angle5_1_1 autoMove_06_01_gkmovemid_Sidestep_Angle5_1_1 NEARKEEPER_04_04_gkmovemid_2_2_BODYTURN_SLANT NEARKEEPER_04_04_gkmovenear_1_1_BODYTURN_SLANT autoMove_11_bodyangle_rolling_slow_3_3_Front_to_Back_mid_michael enum_dummy483 enum_dummy536 enum_dummy564 enum_dummy592 enum_dummy618 enum_dummy623 enum_dummy648 defenseMove_01_parallel_4_3_neardelayback_act068_02 passGetMove_01_run_3_3_f180_act001 .geom angry_shout_M_01 angry_talk_S_02 base_d_end_cup_shout base_g_sliding ef23_neutral_scowl_at ef23_p

OFFSET=0x9da6e0 TERM=TURN
CONTEXT=vice:WANPPPConnection:1 urn:schemas-upnp-org:service:WANIPv6FirewallControl:1 FF05::C friendlyName "serviceType":"%s","serviceId":"%s","controlUrl":"%s","eventSubUrl":"%s","scpdUrl":"%s" FORMALLY_CONNECTED E_NOCHILD DETECT_NAT_ABORTED FREE_TURN_CHANNEL_BINDING_COMPLETE [ %s:%d ][ %d bytes ][ %04x ] HOST_ANY AS align_progress_abormal_end_timout_sec match_not_run_timeout_sec NETWORK_UP_COUNT TRANSPORT_RTT_ RECEIVED_VOICE_DATA_COUNT P2PTURNIO_TURN_RTT_MAX LATENCY_TURN_CONNECT_PEER_MEAN STATS_FORMAT LATENCY_MODE_CONNECT_QUALITY_TEST LATENCY_MODE_ANNTENA_PROCESS_CMD_GET_GAME_SESSION_CHECK_RES RTT_R_V

OFFSET=0x9da7a7 TERM=TURN
CONTEXT=NECTED E_NOCHILD DETECT_NAT_ABORTED FREE_TURN_CHANNEL_BINDING_COMPLETE [ %s:%d ][ %d bytes ][ %04x ] HOST_ANY AS align_progress_abormal_end_timout_sec match_not_run_timeout_sec NETWORK_UP_COUNT TRANSPORT_RTT_ RECEIVED_VOICE_DATA_COUNT P2PTURNIO_TURN_RTT_MAX LATENCY_TURN_CONNECT_PEER_MEAN STATS_FORMAT LATENCY_MODE_CONNECT_QUALITY_TEST LATENCY_MODE_ANNTENA_PROCESS_CMD_GET_GAME_SESSION_CHECK_RES RTT_R_VARIANCE ()Lcom/android/billingclient/api/ProductDetails$OneTimePurchaseOfferDetails; win10_store_id CmdConnectGrpc onlineid network_delay_task CommunicationPrivilegeCheckTask enable_indicator_stats_f

OFFSET=0x9da7ae TERM=TURN
CONTEXT=E_NOCHILD DETECT_NAT_ABORTED FREE_TURN_CHANNEL_BINDING_COMPLETE [ %s:%d ][ %d bytes ][ %04x ] HOST_ANY AS align_progress_abormal_end_timout_sec match_not_run_timeout_sec NETWORK_UP_COUNT TRANSPORT_RTT_ RECEIVED_VOICE_DATA_COUNT P2PTURNIO_TURN_RTT_MAX LATENCY_TURN_CONNECT_PEER_MEAN STATS_FORMAT LATENCY_MODE_CONNECT_QUALITY_TEST LATENCY_MODE_ANNTENA_PROCESS_CMD_GET_GAME_SESSION_CHECK_RES RTT_R_VARIANCE ()Lcom/android/billingclient/api/ProductDetails$OneTimePurchaseOfferDetails; win10_store_id CmdConnectGrpc onlineid network_delay_task CommunicationPrivilegeCheckTask enable_indicator_stats_for_matc

OFFSET=0x9da7c3 TERM=TURN
CONTEXT=ABORTED FREE_TURN_CHANNEL_BINDING_COMPLETE [ %s:%d ][ %d bytes ][ %04x ] HOST_ANY AS align_progress_abormal_end_timout_sec match_not_run_timeout_sec NETWORK_UP_COUNT TRANSPORT_RTT_ RECEIVED_VOICE_DATA_COUNT P2PTURNIO_TURN_RTT_MAX LATENCY_TURN_CONNECT_PEER_MEAN STATS_FORMAT LATENCY_MODE_CONNECT_QUALITY_TEST LATENCY_MODE_ANNTENA_PROCESS_CMD_GET_GAME_SESSION_CHECK_RES RTT_R_VARIANCE ()Lcom/android/billingclient/api/ProductDetails$OneTimePurchaseOfferDetails; win10_store_id CmdConnectGrpc onlineid network_delay_task CommunicationPrivilegeCheckTask enable_indicator_stats_for_match_category sat <SYSTE

OFFSET=0x9e2a79 TERM=TURN
CONTEXT=Texture WidgetSize GetToday strIdBody buttonStr ChildOwner EMenuWaitConditionType::Wakeup EMenuFamilyType::Parent SetMenuWaitCondition RequestForceUpdateList StartExchange EMenuTeamSelectSupportPlayerNum ETeamSelectStep::TEAM_SELECT_STEP_RETURN ETeamSelectStep::TEAM_SELECT_STEP_HOME_LEAGUE_SELECT OnCloseAlertEvent__DelegateSignature EEventAccountType::OBSERVER EMenuSelection::Num EMenuSelection EMenuCommonValid::Invalid EDataLinkageStatus::DATA_LINKAGE_STATUS_NOT_SIGNIN EDataLinkageResult::DATA_LINKAGE_NOT_ENOUGH_OS_VER EMenuDirectNotificationPlateType::SHORT EMenuEulaAgreeEndStep EMenuEulaAgreeFl

OFFSET=0x9e2bf0 TERM=TURN
CONTEXT=on::Num EMenuSelection EMenuCommonValid::Invalid EDataLinkageStatus::DATA_LINKAGE_STATUS_NOT_SIGNIN EDataLinkageResult::DATA_LINKAGE_NOT_ENOUGH_OS_VER EMenuDirectNotificationPlateType::SHORT EMenuEulaAgreeEndStep EMenuEulaAgreeFlowEvent::RETURN EMenuEulaAgreeChoiceKind::CHOICE_NUM IsSkip EMenuEvCompeAnnounceViewStep::PostFadeInAlertPhase1Wait supplementStr strOnlyQuantity GetAuthenticAlertIconText levelIndex IsFinishedEvent EMenuEvCompeMajorCategory::MAJOR_CATEGORY_CHALLENGE EMenuEvCompeEventListBeforeProceedStep::AgeCategory HasRecordEventInEventList IsAiGameMode EMenuEvCompeMainMenuFirstAlertTyp

OFFSET=0x9ea3cb TERM=TURN
CONTEXT=wrap_around_2_2_045_and_090_y0_take1_gabriel dash_10_side_1_4_045_dash_Oriul new_dribble_0_4_f135_out ballTouch_05_5_dribble_touch_far_3_3_000_y0_gabriel moveAdjust_05_Back_2_2_gabriel LongVersion_161107_F054_t01_Mobi_01 nearDefense_04_BODYTURN_Slant_3_3_rightside_STEP_near_gabriel reaction_contact_1_4_090_act071_01 dribblerun_arc_3_3_90_y0_in_act064 traprun_arc_3_3m_f090_y0_in_act064 trap_0_3_135_y3_in_act064 idle_0_3_run_090_push_aside idle_0_3_run_180_jostle dm_miss_idle_0_1_walk_angry_slap_knee_090 dm_miss_run_3_1_walk_angry_f180 tacklefoot_sideways_mid_0_0_f045_act095 tacklefoot_sideways_near

OFFSET=0x9eda0d TERM=TURN
CONTEXT=uncompress_buffer_retry_max enable_error_record NUM_NODES_BEGIN_MATCH RX_LOSS_RATE_MEAN_NPI SELF_AUTOMOVE_COUNT_BURST_L3_MCACTIVE IP_ADDRESS_HOP_1_UDP_END_TEST IP_ADDRESS_HOP_2_UDP_END_TEST IP_ADDRESS_ICMP_END_TEST MATCH_SETTING_STADIUM_ID TURN_QUALITY_BASESESSION_RTT TURN_SESSION_RTT_MEAN LATENCY_TURN_CONNECT_ANY_MAX CONTROL_STYLE_SETTING DCTEST_MEASUREMENT_PROTOCOL SOCKET_ERRORS \s*konami ], LATENCY_NTL_STUNCHECK_PROCESS LATENCY_MODE_ANNTENA_DISP_MATCHING_RESULT SP_REGULATION CS_RESET_UDP_SOCKET_COUNT ACTUAL_MATCH_HZ_MIN ACTUAL_MATCH_HZ_R_VARIANCE ":[ PesSessionManager enable_client_receipt_ac

OFFSET=0x9eda2a TERM=TURN
CONTEXT=nable_error_record NUM_NODES_BEGIN_MATCH RX_LOSS_RATE_MEAN_NPI SELF_AUTOMOVE_COUNT_BURST_L3_MCACTIVE IP_ADDRESS_HOP_1_UDP_END_TEST IP_ADDRESS_HOP_2_UDP_END_TEST IP_ADDRESS_ICMP_END_TEST MATCH_SETTING_STADIUM_ID TURN_QUALITY_BASESESSION_RTT TURN_SESSION_RTT_MEAN LATENCY_TURN_CONNECT_ANY_MAX CONTROL_STYLE_SETTING DCTEST_MEASUREMENT_PROTOCOL SOCKET_ERRORS \s*konami ], LATENCY_NTL_STUNCHECK_PROCESS LATENCY_MODE_ANNTENA_DISP_MATCHING_RESULT SP_REGULATION CS_RESET_UDP_SOCKET_COUNT ACTUAL_MATCH_HZ_MIN ACTUAL_MATCH_HZ_R_VARIANCE ":[ PesSessionManager enable_client_receipt_acknowledge getIntroductoryPric

OFFSET=0x9eda48 TERM=TURN
CONTEXT=EGIN_MATCH RX_LOSS_RATE_MEAN_NPI SELF_AUTOMOVE_COUNT_BURST_L3_MCACTIVE IP_ADDRESS_HOP_1_UDP_END_TEST IP_ADDRESS_HOP_2_UDP_END_TEST IP_ADDRESS_ICMP_END_TEST MATCH_SETTING_STADIUM_ID TURN_QUALITY_BASESESSION_RTT TURN_SESSION_RTT_MEAN LATENCY_TURN_CONNECT_ANY_MAX CONTROL_STYLE_SETTING DCTEST_MEASUREMENT_PROTOCOL SOCKET_ERRORS \s*konami ], LATENCY_NTL_STUNCHECK_PROCESS LATENCY_MODE_ANNTENA_DISP_MATCHING_RESULT SP_REGULATION CS_RESET_UDP_SOCKET_COUNT ACTUAL_MATCH_HZ_MIN ACTUAL_MATCH_HZ_R_VARIANCE ":[ PesSessionManager enable_client_receipt_acknowledge getIntroductoryPriceAmountMicros getOriginalPrice

OFFSET=0xa00bf1 TERM=TURN
CONTEXT=rogress_ready_timeout_sec IPADDR_PEER MATCH_STOP_COUNT_BUF_EMPTY_BURST_L2_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L4_MCACTIVE IDELAY_BUF_SIZE_FOR_INPUT_DELAY_ RTT_ SELF_AUTOMOVE_COUNT SEND_COMMAND_MUST_NOT_DROP_COUNT_RECV NTL_PEER_STATUS TURN_QUALITY_LATEST_RTT P2PTURNIO_P2P_CONNECTING_TIME P2PTURNIO_RTT_VARIANCE_EVALUATION LATENCY_TURN_CONNECT_ANY_MIN SCORE_SITUATION LATENCY_NTL_PUNCHING_RETRY GAMRERELAY_MEASUARE_RESULT_AT_MATCHING MEMPEAK_RENDER_TARGET_POOL_SIZE MEMPEAK_MATCH_FLOW_KIND ADDRV6_CHANGED _DECODE_ SessionImplTry getOriginalJson getPricingPhases isProductDetailsSupported CmdWatchTur

OFFSET=0xa00c0c TERM=TURN
CONTEXT=PADDR_PEER MATCH_STOP_COUNT_BUF_EMPTY_BURST_L2_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L4_MCACTIVE IDELAY_BUF_SIZE_FOR_INPUT_DELAY_ RTT_ SELF_AUTOMOVE_COUNT SEND_COMMAND_MUST_NOT_DROP_COUNT_RECV NTL_PEER_STATUS TURN_QUALITY_LATEST_RTT P2PTURNIO_P2P_CONNECTING_TIME P2PTURNIO_RTT_VARIANCE_EVALUATION LATENCY_TURN_CONNECT_ANY_MIN SCORE_SITUATION LATENCY_NTL_PUNCHING_RETRY GAMRERELAY_MEASUARE_RESULT_AT_MATCHING MEMPEAK_RENDER_TARGET_POOL_SIZE MEMPEAK_MATCH_FLOW_KIND ADDRV6_CHANGED _DECODE_ SessionImplTry getOriginalJson getPricingPhases isProductDetailsSupported CmdWatchTurnAddressData.php OnlineServ

OFFSET=0xa00c2a TERM=TURN
CONTEXT=F_EMPTY_BURST_L2_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L4_MCACTIVE IDELAY_BUF_SIZE_FOR_INPUT_DELAY_ RTT_ SELF_AUTOMOVE_COUNT SEND_COMMAND_MUST_NOT_DROP_COUNT_RECV NTL_PEER_STATUS TURN_QUALITY_LATEST_RTT P2PTURNIO_P2P_CONNECTING_TIME P2PTURNIO_RTT_VARIANCE_EVALUATION LATENCY_TURN_CONNECT_ANY_MIN SCORE_SITUATION LATENCY_NTL_PUNCHING_RETRY GAMRERELAY_MEASUARE_RESULT_AT_MATCHING MEMPEAK_RENDER_TARGET_POOL_SIZE MEMPEAK_MATCH_FLOW_KIND ADDRV6_CHANGED _DECODE_ SessionImplTry getOriginalJson getPricingPhases isProductDetailsSupported CmdWatchTurnAddressData.php OnlineServiceEligibilityCheckTask ETH 10

OFFSET=0xa00c51 TERM=TURN
CONTEXT=UNT_BUF_EMPTY_BURST_L4_MCACTIVE IDELAY_BUF_SIZE_FOR_INPUT_DELAY_ RTT_ SELF_AUTOMOVE_COUNT SEND_COMMAND_MUST_NOT_DROP_COUNT_RECV NTL_PEER_STATUS TURN_QUALITY_LATEST_RTT P2PTURNIO_P2P_CONNECTING_TIME P2PTURNIO_RTT_VARIANCE_EVALUATION LATENCY_TURN_CONNECT_ANY_MIN SCORE_SITUATION LATENCY_NTL_PUNCHING_RETRY GAMRERELAY_MEASUARE_RESULT_AT_MATCHING MEMPEAK_RENDER_TARGET_POOL_SIZE MEMPEAK_MATCH_FLOW_KIND ADDRV6_CHANGED _DECODE_ SessionImplTry getOriginalJson getPricingPhases isProductDetailsSupported CmdWatchTurnAddressData.php OnlineServiceEligibilityCheckTask ETH 100BASE_HALF EKH %4d-%02d-%02dT%02d:%02d:

OFFSET=0xa10549 TERM=TURN
CONTEXT=06_t01_act081 defenseMove_02_1_2_Match_up_center_2_1_act082 dash_02_loop_3_4_Oriul ballTouch_03_3_dribble_player_wrap_around_3_3_045_and_090_y0_gabriel dash_09_idle_0_4_090_dash_Oriul LongVersion_161107_F062_t01_David_01 nearDefense_04_BODYTURN_Slant_2_2_frontback_STEP_near_gabriel nearDribble_04_1_dribble_burst_2_4_f135_y0_oriul tacklefoot_parallel_near_0_0_000_act100 dribblerun_arc_3m_3m_067_y0_in_act064 dribblerun_arc_3m_3_f067_y0_out_act064 dash_05_turn_4_3_090_CRANK gkseeoff_side_react_3_0_y11 tackleshoulder_3_2_interrupt_blast_090_act102 dml_goal_celebrate_0059 dml_goal_celebrate_0066 dml_go

OFFSET=0xa1363f TERM=TURN
CONTEXT=lns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><SOAP-ENV:Body> ServiceType Term GetStatusInfo 1.17.1-Android ## LastAnalyseTransport >> BYPASS E_UHP_READY ALLOC_TURN_PORT_ABORTED PEER_REFLEXIVE FREE_C nativeOnReceivePurchasesUpdated load_timeout_sec SERVNAME_PEER HOP_COUNT_UDP_END_TEST MCLATENCY_ SELF_AUTOMOVE_COUNT_MCACTIVE TURN_QUALITY_BASESESSION_RTT_COUNT P2PTURNIO_P2P_RTT_Variance LATENCY_TURN_GET_TURN_ADDRESS_VARIANCE MANUFACTURER AWAY_SCORE DOWNLOAD_SERVER_STATS_SEND_ LATENCY_NTL_PUNCHING_TIME LATENCY_MODE_PRE_ME

OFFSET=0xa136e5 TERM=TURN
CONTEXT=Info 1.17.1-Android ## LastAnalyseTransport >> BYPASS E_UHP_READY ALLOC_TURN_PORT_ABORTED PEER_REFLEXIVE FREE_C nativeOnReceivePurchasesUpdated load_timeout_sec SERVNAME_PEER HOP_COUNT_UDP_END_TEST MCLATENCY_ SELF_AUTOMOVE_COUNT_MCACTIVE TURN_QUALITY_BASESESSION_RTT_COUNT P2PTURNIO_P2P_RTT_Variance LATENCY_TURN_GET_TURN_ADDRESS_VARIANCE MANUFACTURER AWAY_SCORE DOWNLOAD_SERVER_STATS_SEND_ LATENCY_NTL_PUNCHING_TIME LATENCY_MODE_PRE_MENU_TEAM_DATA_SYNC SP_REGULATION_VALUE RX_LOSS_RATE_MAX ADDR_CHANGED RSSI_MAX RX_LOSS_RATE_R_MAX it->second: disable_kgs_unlock_on_cancelled (I)Ljava/lang/Object; getB

OFFSET=0xa1370b TERM=TURN
CONTEXT=nsport >> BYPASS E_UHP_READY ALLOC_TURN_PORT_ABORTED PEER_REFLEXIVE FREE_C nativeOnReceivePurchasesUpdated load_timeout_sec SERVNAME_PEER HOP_COUNT_UDP_END_TEST MCLATENCY_ SELF_AUTOMOVE_COUNT_MCACTIVE TURN_QUALITY_BASESESSION_RTT_COUNT P2PTURNIO_P2P_RTT_Variance LATENCY_TURN_GET_TURN_ADDRESS_VARIANCE MANUFACTURER AWAY_SCORE DOWNLOAD_SERVER_STATS_SEND_ LATENCY_NTL_PUNCHING_TIME LATENCY_MODE_PRE_MENU_TEAM_DATA_SYNC SP_REGULATION_VALUE RX_LOSS_RATE_MAX ADDR_CHANGED RSSI_MAX RX_LOSS_RATE_R_MAX it->second: disable_kgs_unlock_on_cancelled (I)Ljava/lang/Object; getBasePlanId getSignature nativeOnAcknowl

OFFSET=0xa1372b TERM=TURN
CONTEXT=LOC_TURN_PORT_ABORTED PEER_REFLEXIVE FREE_C nativeOnReceivePurchasesUpdated load_timeout_sec SERVNAME_PEER HOP_COUNT_UDP_END_TEST MCLATENCY_ SELF_AUTOMOVE_COUNT_MCACTIVE TURN_QUALITY_BASESESSION_RTT_COUNT P2PTURNIO_P2P_RTT_Variance LATENCY_TURN_GET_TURN_ADDRESS_VARIANCE MANUFACTURER AWAY_SCORE DOWNLOAD_SERVER_STATS_SEND_ LATENCY_NTL_PUNCHING_TIME LATENCY_MODE_PRE_MENU_TEAM_DATA_SYNC SP_REGULATION_VALUE RX_LOSS_RATE_MAX ADDR_CHANGED RSSI_MAX RX_LOSS_RATE_R_MAX it->second: disable_kgs_unlock_on_cancelled (I)Ljava/lang/Object; getBasePlanId getSignature nativeOnAcknowledgeFinished nativeOnShowInAppMe

OFFSET=0xa13734 TERM=TURN
CONTEXT=PORT_ABORTED PEER_REFLEXIVE FREE_C nativeOnReceivePurchasesUpdated load_timeout_sec SERVNAME_PEER HOP_COUNT_UDP_END_TEST MCLATENCY_ SELF_AUTOMOVE_COUNT_MCACTIVE TURN_QUALITY_BASESESSION_RTT_COUNT P2PTURNIO_P2P_RTT_Variance LATENCY_TURN_GET_TURN_ADDRESS_VARIANCE MANUFACTURER AWAY_SCORE DOWNLOAD_SERVER_STATS_SEND_ LATENCY_NTL_PUNCHING_TIME LATENCY_MODE_PRE_MENU_TEAM_DATA_SYNC SP_REGULATION_VALUE RX_LOSS_RATE_MAX ADDR_CHANGED RSSI_MAX RX_LOSS_RATE_R_MAX it->second: disable_kgs_unlock_on_cancelled (I)Ljava/lang/Object; getBasePlanId getSignature nativeOnAcknowledgeFinished nativeOnShowInAppMessageFini

OFFSET=0xa22d68 TERM=TURN
CONTEXT=01_reverse_loop_parallel_back_3_3_near_gabriel autoMove_03_crank90_loop_2_2_STEP_near_gabriel autoMove_06_zigzag135_side_loop_2_2_STEP_near_gabriel dm_goal_extra_loop_0001 autoMove_00_bodyangle_00_180_00_3_3_near_gabriel nearDefense_04_BODYTURN_Slant_1_1_frontback_STEP_near_gabriel dm_oop_lineback_walkback_1_1_walkback_000 feint_tap_0_3_f090_y0_sole_Ltouch_axisbackin_act097 reaction_overtaken_0_3_180_stagger_short_act064 traprun_arc_3m_3m_090_y0_axisback_in_act064 idle_0_3_run_090_jostle_v2 tacklefoot_sideways_near_0_0_000_act095 gkmovelow_sidestep_roll_1_1_90 dm_oop_beckon_090_parallel_2_2_parall

OFFSET=0xa235ba TERM=TURN
CONTEXT=0_idle enum_dummy331 LongVersion_201123_F027_t02_act068_01 enum_dummy413 enum_dummy420 enum_dummy425 enum_dummy461 autoMove_00_01_gkmovenear_FrontBackLoop_step_Angle5_2_2 NEARKEEPER_03_02_gkmovenear_0_1_0 NEARKEEPER_04_03_gkmovemid_1_1_BODYTURN_SLANT enum_dummy485 enum_dummy500 enum_dummy503 enum_dummy544 enum_dummy545 ShortVersion_201123_F002_t01_act068_01 ShortVersion_201123_F007_t01_act068_02 ShortVersion_201123_F013_t01_act068_01 defenseMove_01_parallel_4_0_090_neardelay_act068 defenseMove_01_parallel_4_3_neardelayback_act068_01 passGetMove_02_feint_run_3_3_f180_act068 gkrise_sideways_l_0_3_f0

OFFSET=0xa2619f TERM=TURN
CONTEXT=P_HEADER CHANNEL MappingTestID Connection: Keep-Alive minor <?xml version="1.0"?> NewProtocol AddPinhole ## StunAgentDump isEnabled LOG_ACTIVE UhpFinalize E_HOSTDOWN E_MUTEX_SRCH HTTP_SESSION_ERROR UPNP_DELETE_PORT_FORWARDING_ERROR ALLOC_TURN_PORT_COMPLETE PEER_RELAYED command_auto_retry windows match_sync_failed_timeout_sec NSW ABNORMAL_END_FLAG HOP_COUNT_ICMP_BEGIN_TEST RX_RLOSS_RATE_ SELF_AUTOMOVE_COUNT_BURST_L2_MCACTIVE TURN_QUALITY_BASESESSION_TRANSPORT_RTT TURN_QUALITY_DEGRADED INDICATOR_DISP_NUM CONTROL_STYLE_FILTERING ABNORMALEND_PROBLEM_FLAG LOWEST LATENCY_NTL_PUNCHING_PRE LATENCY_MODE_

OFFSET=0xa2625d TERM=TURN
CONTEXT=ION_ERROR UPNP_DELETE_PORT_FORWARDING_ERROR ALLOC_TURN_PORT_COMPLETE PEER_RELAYED command_auto_retry windows match_sync_failed_timeout_sec NSW ABNORMAL_END_FLAG HOP_COUNT_ICMP_BEGIN_TEST RX_RLOSS_RATE_ SELF_AUTOMOVE_COUNT_BURST_L2_MCACTIVE TURN_QUALITY_BASESESSION_TRANSPORT_RTT TURN_QUALITY_DEGRADED INDICATOR_DISP_NUM CONTROL_STYLE_FILTERING ABNORMALEND_PROBLEM_FLAG LOWEST LATENCY_NTL_PUNCHING_PRE LATENCY_MODE_SESSION LATENCY_MODE_SESSION_POLLING_CMD_GET_GAME_SESSION MATCH_COUNT BPS_RECEIVE_ UE_THREAD_ELAPSED_SINCE_LAST_UPDATED RECORED_TIME LAST_IPADDR DATA_TYPE RX_RLOSS_RATE_R_MAX Number of purch

OFFSET=0xa26284 TERM=TURN
CONTEXT=RROR ALLOC_TURN_PORT_COMPLETE PEER_RELAYED command_auto_retry windows match_sync_failed_timeout_sec NSW ABNORMAL_END_FLAG HOP_COUNT_ICMP_BEGIN_TEST RX_RLOSS_RATE_ SELF_AUTOMOVE_COUNT_BURST_L2_MCACTIVE TURN_QUALITY_BASESESSION_TRANSPORT_RTT TURN_QUALITY_DEGRADED INDICATOR_DISP_NUM CONTROL_STYLE_FILTERING ABNORMALEND_PROBLEM_FLAG LOWEST LATENCY_NTL_PUNCHING_PRE LATENCY_MODE_SESSION LATENCY_MODE_SESSION_POLLING_CMD_GET_GAME_SESSION MATCH_COUNT BPS_RECEIVE_ UE_THREAD_ELAPSED_SINCE_LAST_UPDATED RECORED_TIME LAST_IPADDR DATA_TYPE RX_RLOSS_RATE_R_MAX Number of purchases: %d CmdGetProductList.php need_roo

OFFSET=0xa37587 TERM=TURN
CONTEXT=Match\Online\MatchOnlineNegotiator.cpp m_autoMemberChange m_useMultiFormation GOAL_KEEPER_DODGE SHOOT DEMO_CURSOL_PLAYER ANIME_SHOOT ANIME_QUICK_RESTART_SHORT_PASS ANIME_SEAMLESS_CORNERKICK_READY FEINT_KIND_DRAWOPENCLOSE FEINT_KIND_ELASTICOTURN FEINT_KIND_SCISSORS_IN_L FEINT_KIND_ROULETTE_RIBERY_R FEINT_KIND_OUTIN_L FEINT_KIND_DOUBLETOUCH_BALLROLL_R FEINT_KIND_DOUBLETOUCH_BALLROLL_RABONA_R FEINT_KIND_RAINBOW_FLICK_L L3 OFFENCE_X DEFENCE_B SETPLAY_ACTION_DECIDE KICKER_SETTING_CHANGE FORFEITED_GAME TUTORIAL_CONE_KIND_NORMAL SUGOROKU_RESTART_KIND_NORMAL cpk_dat/common/match/path_to_glory_replay/path_

OFFSET=0xa38923 TERM=TURN
CONTEXT=TE is_pf_play_history_key_set NtlUpdateThread LIFETIME REALM REQUESTED_ADDRESS_FAMILY INDICATION LOCATION SOAPAction: "%s#%s" modelName udp "%s":[ [ %d ] DeletePortForwarding Fail. ${"%s":%d} ## Turn Status ${"rtt:":%d} E_ADDRINUSE ALLOC_TURN_PORT_ERROR FREE_TURN_PORT_COMPLETE ALLOC_TURN_CHANNEL_BINDING_COMPLETE START_SERVER_UDP_SESSION_COMPLETE KEEPALIVE_FAKE PEER_TURN %63s%X%X%X%d%d%d%X%d%d%d interval_factor PS5 timeout widevine_id use_cronet MODELNAME_PEERS NUM_LOCAL_GUESTS_BEGIN_MATCH MATCH_CONDITION IDELAY_BUF_SIZE_STANDARD_VALUE_ MATCH_STOP_COUNT_BUF_EMPTY_BURST_L5_MCACTIVE RECEIVED_INVAL

OFFSET=0xa38938 TERM=TURN
CONTEXT=_key_set NtlUpdateThread LIFETIME REALM REQUESTED_ADDRESS_FAMILY INDICATION LOCATION SOAPAction: "%s#%s" modelName udp "%s":[ [ %d ] DeletePortForwarding Fail. ${"%s":%d} ## Turn Status ${"rtt:":%d} E_ADDRINUSE ALLOC_TURN_PORT_ERROR FREE_TURN_PORT_COMPLETE ALLOC_TURN_CHANNEL_BINDING_COMPLETE START_SERVER_UDP_SESSION_COMPLETE KEEPALIVE_FAKE PEER_TURN %63s%X%X%X%d%d%d%X%d%d%d interval_factor PS5 timeout widevine_id use_cronet MODELNAME_PEERS NUM_LOCAL_GUESTS_BEGIN_MATCH MATCH_CONDITION IDELAY_BUF_SIZE_STANDARD_VALUE_ MATCH_STOP_COUNT_BUF_EMPTY_BURST_L5_MCACTIVE RECEIVED_INVALID_COUNT MATCH_SETTIN

OFFSET=0xa38951 TERM=TURN
CONTEXT=LIFETIME REALM REQUESTED_ADDRESS_FAMILY INDICATION LOCATION SOAPAction: "%s#%s" modelName udp "%s":[ [ %d ] DeletePortForwarding Fail. ${"%s":%d} ## Turn Status ${"rtt:":%d} E_ADDRINUSE ALLOC_TURN_PORT_ERROR FREE_TURN_PORT_COMPLETE ALLOC_TURN_CHANNEL_BINDING_COMPLETE START_SERVER_UDP_SESSION_COMPLETE KEEPALIVE_FAKE PEER_TURN %63s%X%X%X%d%d%d%X%d%d%d interval_factor PS5 timeout widevine_id use_cronet MODELNAME_PEERS NUM_LOCAL_GUESTS_BEGIN_MATCH MATCH_CONDITION IDELAY_BUF_SIZE_STANDARD_VALUE_ MATCH_STOP_COUNT_BUF_EMPTY_BURST_L5_MCACTIVE RECEIVED_INVALID_COUNT MATCH_SETTING_TURFLENGTH TURN_CHANGEO

OFFSET=0xa389a5 TERM=TURN
CONTEXT=lName udp "%s":[ [ %d ] DeletePortForwarding Fail. ${"%s":%d} ## Turn Status ${"rtt:":%d} E_ADDRINUSE ALLOC_TURN_PORT_ERROR FREE_TURN_PORT_COMPLETE ALLOC_TURN_CHANNEL_BINDING_COMPLETE START_SERVER_UDP_SESSION_COMPLETE KEEPALIVE_FAKE PEER_TURN %63s%X%X%X%d%d%d%X%d%d%d interval_factor PS5 timeout widevine_id use_cronet MODELNAME_PEERS NUM_LOCAL_GUESTS_BEGIN_MATCH MATCH_CONDITION IDELAY_BUF_SIZE_STANDARD_VALUE_ MATCH_STOP_COUNT_BUF_EMPTY_BURST_L5_MCACTIVE RECEIVED_INVALID_COUNT MATCH_SETTING_TURFLENGTH TURN_CHANGEOVER_REASON TURN_SESSION_RTT_LATEST LATENCY_TURN_RESOLVING_NAME_MEAN HOME_SCORE LATEN

OFFSET=0xa38ab1 TERM=TURN
CONTEXT=d interval_factor PS5 timeout widevine_id use_cronet MODELNAME_PEERS NUM_LOCAL_GUESTS_BEGIN_MATCH MATCH_CONDITION IDELAY_BUF_SIZE_STANDARD_VALUE_ MATCH_STOP_COUNT_BUF_EMPTY_BURST_L5_MCACTIVE RECEIVED_INVALID_COUNT MATCH_SETTING_TURFLENGTH TURN_CHANGEOVER_REASON TURN_SESSION_RTT_LATEST LATENCY_TURN_RESOLVING_NAME_MEAN HOME_SCORE LATENCY_MODE_SESSION_CMD_GET_TURN_SERVER_LIST LATENCY_MODE_CONNECT_MODE_MULTIPLAY MAIN_THREAD_LAST_UPDATED (Ljava/lang/String;[Ljava/lang/String;)V (Lcom/android/billingclient/api/BillingResult;Lcom/android/billingclient/api/Purchase;)V gps_adid steam_item_id CmdVerifyUser

OFFSET=0xa38ac8 TERM=TURN
CONTEXT=timeout widevine_id use_cronet MODELNAME_PEERS NUM_LOCAL_GUESTS_BEGIN_MATCH MATCH_CONDITION IDELAY_BUF_SIZE_STANDARD_VALUE_ MATCH_STOP_COUNT_BUF_EMPTY_BURST_L5_MCACTIVE RECEIVED_INVALID_COUNT MATCH_SETTING_TURFLENGTH TURN_CHANGEOVER_REASON TURN_SESSION_RTT_LATEST LATENCY_TURN_RESOLVING_NAME_MEAN HOME_SCORE LATENCY_MODE_SESSION_CMD_GET_TURN_SERVER_LIST LATENCY_MODE_CONNECT_MODE_MULTIPLAY MAIN_THREAD_LAST_UPDATED (Ljava/lang/String;[Ljava/lang/String;)V (Lcom/android/billingclient/api/BillingResult;Lcom/android/billingclient/api/Purchase;)V gps_adid steam_item_id CmdVerifyUserCanBuy.php CmdWatchTurn

OFFSET=0xa38ae8 TERM=TURN
CONTEXT=ODELNAME_PEERS NUM_LOCAL_GUESTS_BEGIN_MATCH MATCH_CONDITION IDELAY_BUF_SIZE_STANDARD_VALUE_ MATCH_STOP_COUNT_BUF_EMPTY_BURST_L5_MCACTIVE RECEIVED_INVALID_COUNT MATCH_SETTING_TURFLENGTH TURN_CHANGEOVER_REASON TURN_SESSION_RTT_LATEST LATENCY_TURN_RESOLVING_NAME_MEAN HOME_SCORE LATENCY_MODE_SESSION_CMD_GET_TURN_SERVER_LIST LATENCY_MODE_CONNECT_MODE_MULTIPLAY MAIN_THREAD_LAST_UPDATED (Ljava/lang/String;[Ljava/lang/String;)V (Lcom/android/billingclient/api/BillingResult;Lcom/android/billingclient/api/Purchase;)V gps_adid steam_item_id CmdVerifyUserCanBuy.php CmdWatchTurnAddressData ; EHH EKF XSX sun E

OFFSET=0xa38b29 TERM=TURN
CONTEXT=Y_BUF_SIZE_STANDARD_VALUE_ MATCH_STOP_COUNT_BUF_EMPTY_BURST_L5_MCACTIVE RECEIVED_INVALID_COUNT MATCH_SETTING_TURFLENGTH TURN_CHANGEOVER_REASON TURN_SESSION_RTT_LATEST LATENCY_TURN_RESOLVING_NAME_MEAN HOME_SCORE LATENCY_MODE_SESSION_CMD_GET_TURN_SERVER_LIST LATENCY_MODE_CONNECT_MODE_MULTIPLAY MAIN_THREAD_LAST_UPDATED (Ljava/lang/String;[Ljava/lang/String;)V (Lcom/android/billingclient/api/BillingResult;Lcom/android/billingclient/api/Purchase;)V gps_adid steam_item_id CmdVerifyUserCanBuy.php CmdWatchTurnAddressData ; EHH EKF XSX sun EnableBroadcasting grpc.service_config hooks_[static_cast<size_t>(

OFFSET=0xa4009c TERM=TURN
CONTEXT=tandardChanceDealType::TYPE_NUM CmnMatchLabelLengthType::SHORT_LONG ECmnMatchLabelKind::DREAM GuideOff TouchedCloseCallbackEventDispatcher__DelegateSignature ECommonWidgetLabelKind::FRAME_OUT_PROCEED_END ECommonWidgetLabelKind::FRAME_OUT_RETURN_END ECommonWidgetLabelKind::STATE_INACTIVE ECommonWidgetLabelKind::NONE ESituationType CrowdInstanceParam UpperLeftUV ECustomStadiumParamType::PitchsideObject5 EDataStoreValueType::Float GetValueAsObject VectorValue EDemoAudiFlagNum::Num ShootingLocationChanged GetCompeOriginalEmblemId GetViewPlayerPoseNo IsDragSorce bReload EDebugInterruptionTestKindFlowMa

OFFSET=0xa4b133 TERM=TURN
CONTEXT=ta play_data CMD_SET_USER_EULA_INFO gamerelay_measure_result CMD_UPDATE_TERMS_TO_SERVICE CmdGetEventMissionAiMatchList.php CmdGetEventCompeGroupStageDraw.php CMD_BUY_ML_EVENT_LIFE SE_DIALOG_RELEASED room_kind is_exist_request_to_join CMD_RETURN_ROOM CmdDeleteMyclubSkill.php CMD_DELETE_MYCLUB_SQUAD base_gameplayer_id CMD_USE_MYCLUB_CAREERPLAN auto_item_list CmdUseMyclubStandardDraft.php CmdGetVotingInfo.php top_goal_value top_assist_player_id CMD_CHECK_USER_COMPE_PASSWORD CmdGetUserCompeCurrentEntryInfo.php last_entry_compe_id CMD_GET_USER_COMPE_OBSERVE_MATCH_LIST team_power_default fame_limited_li

OFFSET=0xa4b7d1 TERM=TURN
CONTEXT=S STOP_UDP_HOLE_PUNCHING_ERROR CHECK_STUN_RTT_COMPLETE [ %s:%d ][ %d bytes ] HOST_RELAY is_enable_all_command iOs sa_hud_low IPADDRV6_PEER SESSION_MODE GAME_MODE MATCH_STOP_MAX_ROLLING_COUNT_BUF_EMPTY_IV2_MCACTIVE RECEIVED_INVALID_LENGTH TURN_QUALITY_RTT_EWMA_PENALTY DCTEST_RECOMMENDED_REGION LATENCY_MODE_ANNTENA_CMD_GET_GAMEID RTT_MAX RSSI_MEAN DISPRESION _DWN_ID_ getOrderId getAccountIdentifiers hashCode (Lcom/android/billingclient/api/BillingResult;)V nativeOnBuyFinished callback empty. Number of details: %d pw PaidServiceEligibilityCheckTask 1000BASE_HALF CmdSetOnlineStats jp/konami/android/

OFFSET=0xa5b6f9 TERM=TURN
CONTEXT=stop_leftside_rightside_2_2_STEP_near_gabriel autoMove_02_reverse_stop_rightfront_leftback_3_3_STEP_near_gabriel autoMove_07_ragged45_front_loop_3_3_near_gabriel autoMove_06_dribble_zigzag135_side_loop_3_3_STEP_near_gabriel autoMove_33_IDLETURN_Front_45_90_135_180_near_gabriel moveAdjust_05_Side_2_2_gabriel nearDefense_04_BODYTURN_Slant_3_3_frontback_reverse_STEP_near_gabriel autoMove_02_dribble_reverse_stop_leftfront_rightback_2_2_STEP_near_gabriel gkblock_lie_s02b01_0_0_y04_090 gkdeflect_f05_3_0_y00_090 gkdeflect_f05_3_0_y02_090 traprun_arc_3m_3m_f045_y0_in_act064 dml_goal_celebrate_0208 dash_05

OFFSET=0xa5b751 TERM=TURN
CONTEXT=ck_3_3_STEP_near_gabriel autoMove_07_ragged45_front_loop_3_3_near_gabriel autoMove_06_dribble_zigzag135_side_loop_3_3_STEP_near_gabriel autoMove_33_IDLETURN_Front_45_90_135_180_near_gabriel moveAdjust_05_Side_2_2_gabriel nearDefense_04_BODYTURN_Slant_3_3_frontback_reverse_STEP_near_gabriel autoMove_02_dribble_reverse_stop_leftfront_rightback_2_2_STEP_near_gabriel gkblock_lie_s02b01_0_0_y04_090 gkdeflect_f05_3_0_y00_090 gkdeflect_f05_3_0_y02_090 traprun_arc_3m_3m_f045_y0_in_act064 dml_goal_celebrate_0208 dash_05_turn_4_4_045_CRANK_Ortega pk_enclose_hiza dml_goal_celebrate_0069 dml_goal_celebrate_00

OFFSET=0xa5c15f TERM=TURN
CONTEXT=_F034_t01_act071_02 bench_sit_cross_leg bench_sit_think_2 autoMove_00_01_gkmovenear_FrontBackLoop_slant_Angle5_3_3 autoMove_00_gkmovenear_step_ChageAngle01_1_1 autoMove_08_01_gkmovemid_Sidestep_Angle5_1_1 NEARKEEPER_04_02_gkmovemid_2_2_BODYTURN_SLANT enum_dummy501 enum_dummy552 enum_dummy562 enum_dummy579 enum_dummy581 enum_dummy591 enum_dummy604 enum_dummy641 enum_dummy653 enum_dummy655 passGetMove_02_feint_run_3_3_f225_act001 gkrise_faceup_0_3_f060 cpk_dat/common/anime/FoxAnim/Face/face_base_anime_file0.mtar skf_NMdriver angry_talk_M_03 base_d_fuan base_d_itai dml_song_soft neut neut_breath_hit_

OFFSET=0xa5eb1f TERM=TURN
CONTEXT=_from_file Lifetime expired. (Lifetime = Unknown error. (error code = confirmed platform_kind CHANGE_ADDRESS RP_RAND_SEED RP_HEARTBEAT RP_P2P_SYNC NewRSIPAvailable ## [ NTL WARNING ][ %d ] GetPeerStatusEx Error [ pid %d ][ %s ][ %08x ] E_TURN_QUOTA_ERROR HTTP_SESSION_COMPLETE HTTP_SESSION_ABORTED START_UDP_HOLE_PUNCHING_COMPLETE START_UDP_HOLE_PUNCHING_PROGRESS ST_UHP SND ipv4only.arpa --/--[--:--:--.---](%02d:%02d:%02d) enabel_all_command_cancel INDICATOR_STATS_RECORDER Xbx giveup_byte_per_sec NATTYPE_PEER LINK_TYPE_PEERS IDELAY_BUF_SIZE_ TURN_OFF_COMMUNICATE_COUNT LATENCY_SESSION_ESTABLISH IP_

OFFSET=0xa5ec53 TERM=TURN
CONTEXT=P_HOLE_PUNCHING_COMPLETE START_UDP_HOLE_PUNCHING_PROGRESS ST_UHP SND ipv4only.arpa --/--[--:--:--.---](%02d:%02d:%02d) enabel_all_command_cancel INDICATOR_STATS_RECORDER Xbx giveup_byte_per_sec NATTYPE_PEER LINK_TYPE_PEERS IDELAY_BUF_SIZE_ TURN_OFF_COMMUNICATE_COUNT LATENCY_SESSION_ESTABLISH IP_ADDRESS_HOP_1_ICMP_BEGIN_TEST BACKGROUND_COUNTS P2PTURNIO_P2P_RTT_Max P2PTURNIO_RTT_MAX_EVALUATION HEADER GAME_RESULT GAME_SERVER_STATS_ MEMPEAK_WIDGET_HASH SURVEY_ID_0 RX_RLOSS_RATE_MAX LAST_SERVNAMEV6 pes22-game.cs.konami.net .txt -----BEGIN PUBLIC KEY----- MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEApC/7

OFFSET=0xa5ecbe TERM=TURN
CONTEXT=:%02d:%02d) enabel_all_command_cancel INDICATOR_STATS_RECORDER Xbx giveup_byte_per_sec NATTYPE_PEER LINK_TYPE_PEERS IDELAY_BUF_SIZE_ TURN_OFF_COMMUNICATE_COUNT LATENCY_SESSION_ESTABLISH IP_ADDRESS_HOP_1_ICMP_BEGIN_TEST BACKGROUND_COUNTS P2PTURNIO_P2P_RTT_Max P2PTURNIO_RTT_MAX_EVALUATION HEADER GAME_RESULT GAME_SERVER_STATS_ MEMPEAK_WIDGET_HASH SURVEY_ID_0 RX_RLOSS_RATE_MAX LAST_SERVNAMEV6 pes22-game.cs.konami.net .txt -----BEGIN PUBLIC KEY----- MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEApC/7GywWS+F2J3/GcD2W QiRAhGOp7Y8VkMThCczHTd/ygGmuCSH0312p+9u0vZv/v5MyuAWK8Gm9jbZuDwAY uWKhgFCc4p9xoAMmLBzLoog81

OFFSET=0xa5ecd4 TERM=TURN
CONTEXT=_command_cancel INDICATOR_STATS_RECORDER Xbx giveup_byte_per_sec NATTYPE_PEER LINK_TYPE_PEERS IDELAY_BUF_SIZE_ TURN_OFF_COMMUNICATE_COUNT LATENCY_SESSION_ESTABLISH IP_ADDRESS_HOP_1_ICMP_BEGIN_TEST BACKGROUND_COUNTS P2PTURNIO_P2P_RTT_Max P2PTURNIO_RTT_MAX_EVALUATION HEADER GAME_RESULT GAME_SERVER_STATS_ MEMPEAK_WIDGET_HASH SURVEY_ID_0 RX_RLOSS_RATE_MAX LAST_SERVNAMEV6 pes22-game.cs.konami.net .txt -----BEGIN PUBLIC KEY----- MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEApC/7GywWS+F2J3/GcD2W QiRAhGOp7Y8VkMThCczHTd/ygGmuCSH0312p+9u0vZv/v5MyuAWK8Gm9jbZuDwAY uWKhgFCc4p9xoAMmLBzLoog81VWwQERu4QHRrH/p5z4G5I7

OFFSET=0xa6ee35 TERM=TURN
CONTEXT=tle_f_0_0_f090_act097 autoMove_32_dribble_go_to_2_2_mid_gabriel new_dribbleslide180_3_4_090_in autoMove_02_reverse_stop_leftfront_rightback_3_3_near_gabriel moveAdjust_05_Front_2_2_gabriel moveAdjust_05_Front_3_3_gabriel nearDefense_04_BODYTURN_Slant_3_3_rightfront_STEP_near_gabriel gkdeflect_f05_3_0_y08_045 dm_oop_lineup_f135_idle_0_1_walk_045 gkcatchslideback_f01_3_0_y08_135 gkcatchslideback_f02_3_0_y00_135 gkdeflectlate_s02_0_0_y08 dm_oop_waitpose_f090_idle_0_2_run_045 dml_goal_celebrate_0209 dml_goal_celebrate_0213 dm_miss_idle_0_1_walkback_apologize_twohand_180 js_run_dodge_090_set01_3_3_090_

OFFSET=0xa6f5ed TERM=TURN
CONTEXT=334 LongVersion_201123_F017_t01_act068_02 enum_dummy395 enum_dummy424 autoMove_00_gkmovemid_step_ChageAngle01_2_2 autoMove_04_01_gkmovenear_Sidestep_Angle5_1_1 autoMove_07_01_gkmovemid_Sidestep_Angle5_3_3 NEARKEEPER_04_02_gkmovemid_3_3_BODYTURN_SLANT enum_dummy469 enum_dummy490 enum_dummy499 enum_dummy502 ShortVersion_201123_F002_t01_act071_02 enum_dummy649 block_3_0_y01_f090_act079 defenseMove_01_parallel_3_4_act068 gkrise_sideways_l_0_3_060_hand cpk_dat/common/anime/FoxAnim/Hand/hand_anime_file0.mtar angry_talk_L_01 base_d_ent_sinken base_d_yusyou_warai base_g_kp_kuisibari bitter_mho neut_breath

OFFSET=0xa72514 TERM=TURN
CONTEXT=uuid":"%s","srv":"%s"} ${"ctx":[%d,%d,%d,"%s",%d,%d,%d,%d]} nan E_MUTEX_BUSY %li nn_manual_blocklist_update SEND_COMMAND_DROP_COUNT_BURST_L2 SELF_AUTOMOVE_COUNT_BURST_L5_MCACTIVE NTL_PEER_CLOSE_COUNT IP_ADDRESS_HOP_1_ICMP_END_TEST LATENCY_TURN_CONNECT_UDP_VARIANCE CMD_FINISHED_COUNT_GRPC DOWNLOAD_SERVER_STATS_RECV_ THERMAL_ AGING_RESULT_ID RX_RLOSS_RATE_MEAN getPriceCurrencyCode getFormattedPrice getBillingCycleCount pf_errcode_number product_list image_kind disable ObserveNetworkDelayTask utilconnectcheck MOBILE_2G X36 grpc.min_reconnect_backoff_ms grpc.socket_mutator ((alignment - 1) & alignmen

OFFSET=0xa81b23 TERM=TURN
CONTEXT=ble_reverse_loop_front_back_2_2_STEP_near_gabriel autoMove_03_dribble_crank90_loop_1_1_STEP_near_gabriel autoMove_05_dribble_zigzag135_front_loop_1_1_STEP_near_gabriel new_dribble_0_4_f090_out autoMove_32_go_to_2_2_near_gabriel autoMove_35_TURNCANCEL_Slant_3_3_f090_090_180_STEP_near_gabriel dash_05_turn_4_4_045_CRANK_Oriul dash_05_turn_4_4_090_CRANK_Oriul autoMove_01_dribble_reverse_loop_slant_backslant_2_2_STEP_near_gabriel gkmovehigh_idle_0_0_045_ball gkdeflectlate_s04_0_0_y10 gkblockcover_f01_0_0_y00 dribblerun_arc_3_3m_67_y0_in_act097 traprun_arc_3_3m_090_y0_in_act064 dash_05_turn_4_4_090_CRAN

OFFSET=0xa83f6b TERM=TURN
CONTEXT=GK ANIME_SLIDING ANIME_FREEKICK_LONGPASS ANIME_FREEKICK2ND_SHORTPASS ANIME_KP_PUNCH ANIME_SUB_MEMBER_ACTION FEINT_KIND_NUTMEG FEINT_KIND_BODYFAKE_R FEINT_KIND_ONETIME_L FEINT_KIND_ELASTICO_L FEINT_KIND_ELASTICO_REVERSE_R FEINT_KIND_ELASTICOTURN_L FEINT_KIND_ROULETTE_ONETOUCH_R GOAL_KICK_KIND EX_2ND TIME_UP PATH_TO_GLORY_RESTART_KIND_GOAL_KICK PATH_TO_GLORY_OBJECT_KIND_RUN_MARKER PATH_TO_GLORY_OBJECT_KIND_CONE_GATE_POINT cpk_dat/common/match/path_to_glory_replay/path_to_glory_replay_11.rep cpk_dat/common/match/tutorial_replay/tutorial_replay_passing_01.rep cpk_dat/common/match/tutorial_replay/tutor

OFFSET=0xa852ac TERM=TURN
CONTEXT=DD -%s command_adaptive_retry link_down_check_enable xbx R_VARIANCE NETWORK_STATUS RX_BPS_ EXECUTED_COMMAND_COUNT SEND_COMMAND_DROP_COUNT_MCACTIVE MATCH_STOP_COUNT_SELF_BUF_EMPTY RECEIVED_FROM_UNKNOWN_PEER_LENGTH IP_ADDRESS_ICMP_BEGIN_TEST TURN_QUALITY_BASE_RTT_COUNT TURN_QUALITY_DEGRADATIONSESSION_RTT_MEAN TURN_QUALITY_DEGRADATIONSESSION_TRANSPORT_RTT_COUNT IPV4 PROTO_OPT_HASH REVISION :[ LATENCY_NTL_PUNCHING_PROCESS MEMPEAK_USED_PHYSICAL MEMPEAK_WINDOW_HASH MEMPEAK_MATCH_STATE SURVEY_ANSWER_0 RX_RLOSS_RATE_MIN getCountryCode CmdUnsubscribeGrpc.php CmdWatchNotice.php turn_time_limit try_count WiM

OFFSET=0xa852c8 TERM=TURN
CONTEXT=y link_down_check_enable xbx R_VARIANCE NETWORK_STATUS RX_BPS_ EXECUTED_COMMAND_COUNT SEND_COMMAND_DROP_COUNT_MCACTIVE MATCH_STOP_COUNT_SELF_BUF_EMPTY RECEIVED_FROM_UNKNOWN_PEER_LENGTH IP_ADDRESS_ICMP_BEGIN_TEST TURN_QUALITY_BASE_RTT_COUNT TURN_QUALITY_DEGRADATIONSESSION_RTT_MEAN TURN_QUALITY_DEGRADATIONSESSION_TRANSPORT_RTT_COUNT IPV4 PROTO_OPT_HASH REVISION :[ LATENCY_NTL_PUNCHING_PROCESS MEMPEAK_USED_PHYSICAL MEMPEAK_WINDOW_HASH MEMPEAK_MATCH_STATE SURVEY_ANSWER_0 RX_RLOSS_RATE_MIN getCountryCode CmdUnsubscribeGrpc.php CmdWatchNotice.php turn_time_limit try_count WiM enable_indicator_stats_for_

OFFSET=0xa852f1 TERM=TURN
CONTEXT=ETWORK_STATUS RX_BPS_ EXECUTED_COMMAND_COUNT SEND_COMMAND_DROP_COUNT_MCACTIVE MATCH_STOP_COUNT_SELF_BUF_EMPTY RECEIVED_FROM_UNKNOWN_PEER_LENGTH IP_ADDRESS_ICMP_BEGIN_TEST TURN_QUALITY_BASE_RTT_COUNT TURN_QUALITY_DEGRADATIONSESSION_RTT_MEAN TURN_QUALITY_DEGRADATIONSESSION_TRANSPORT_RTT_COUNT IPV4 PROTO_OPT_HASH REVISION :[ LATENCY_NTL_PUNCHING_PROCESS MEMPEAK_USED_PHYSICAL MEMPEAK_WINDOW_HASH MEMPEAK_MATCH_STATE SURVEY_ANSWER_0 RX_RLOSS_RATE_MIN getCountryCode CmdUnsubscribeGrpc.php CmdWatchNotice.php turn_time_limit try_count WiM enable_indicator_stats_for_answered mini_conn_stats conn_report %s_%

OFFSET=0xa9809d TERM=TURN
CONTEXT=ONBIND |->> [ %s ][ 0x%08x ] 01-SoapAction: "%s#%s" WANIPConnection "buildUrl":"%s" G:\PES22HC\Dev-600Series\Source\Shared\cobra\NatTraversal\NTL\ntl\NtlHelper.cpp LogEnable # SocketError [ %d ] CONNECTED FORMALLY_TIMEOUT E_CONNRESET FREE_TURN_PORT_ERROR START_UDP_HOLE_PUNCHING_ADVICE_CANCEL_LOCAL dhcp.%s.gateway default_timeout_max ntl_multicast_permission NUM_NODES_END_MATCH LINK_TYPE RECEIVED_VOICE_DATA_COUNT_INMATCH MAIN_THREAD_ACTUAL_HZ_ PID MEMORY_VIRTUAL_PEAK_USED_KiB_ TURN_QUALITY_BASESESSION_TRANSPORT_RTT_COUNT LATENCY_TURN_GET_TURN_ADDRESS_MEAN MATCH_MOVE_INPUT_TIME_SEC TURN_UNKNOWN DCT

OFFSET=0xa9818f TERM=TURN
CONTEXT=RN_PORT_ERROR START_UDP_HOLE_PUNCHING_ADVICE_CANCEL_LOCAL dhcp.%s.gateway default_timeout_max ntl_multicast_permission NUM_NODES_END_MATCH LINK_TYPE RECEIVED_VOICE_DATA_COUNT_INMATCH MAIN_THREAD_ACTUAL_HZ_ PID MEMORY_VIRTUAL_PEAK_USED_KiB_ TURN_QUALITY_BASESESSION_TRANSPORT_RTT_COUNT LATENCY_TURN_GET_TURN_ADDRESS_MEAN MATCH_MOVE_INPUT_TIME_SEC TURN_UNKNOWN DCTEST_BEST_ROUTE_RESULT ABNORMALEND_REASON_FROM_SERVER OSVERSION LATENCY_MODE_MATCHING RTT_MEAN TRANSPORT_RTT_R_VARIANCE RSSI_R_MIN _CHCK_PRIVE_ Store jp/konami/android/common/iab/KonamiIabBaseNativeActivity product_id 100BASE_FULL MOBILE enabl

OFFSET=0xa981c4 TERM=TURN
CONTEXT=OCAL dhcp.%s.gateway default_timeout_max ntl_multicast_permission NUM_NODES_END_MATCH LINK_TYPE RECEIVED_VOICE_DATA_COUNT_INMATCH MAIN_THREAD_ACTUAL_HZ_ PID MEMORY_VIRTUAL_PEAK_USED_KiB_ TURN_QUALITY_BASESESSION_TRANSPORT_RTT_COUNT LATENCY_TURN_GET_TURN_ADDRESS_MEAN MATCH_MOVE_INPUT_TIME_SEC TURN_UNKNOWN DCTEST_BEST_ROUTE_RESULT ABNORMALEND_REASON_FROM_SERVER OSVERSION LATENCY_MODE_MATCHING RTT_MEAN TRANSPORT_RTT_R_VARIANCE RSSI_R_MIN _CHCK_PRIVE_ Store jp/konami/android/common/iab/KonamiIabBaseNativeActivity product_id 100BASE_FULL MOBILE enable_indicator_stats_for_game_mode grpc.max_concurrent_s

OFFSET=0xa981cd TERM=TURN
CONTEXT=.%s.gateway default_timeout_max ntl_multicast_permission NUM_NODES_END_MATCH LINK_TYPE RECEIVED_VOICE_DATA_COUNT_INMATCH MAIN_THREAD_ACTUAL_HZ_ PID MEMORY_VIRTUAL_PEAK_USED_KiB_ TURN_QUALITY_BASESESSION_TRANSPORT_RTT_COUNT LATENCY_TURN_GET_TURN_ADDRESS_MEAN MATCH_MOVE_INPUT_TIME_SEC TURN_UNKNOWN DCTEST_BEST_ROUTE_RESULT ABNORMALEND_REASON_FROM_SERVER OSVERSION LATENCY_MODE_MATCHING RTT_MEAN TRANSPORT_RTT_R_VARIANCE RSSI_R_MIN _CHCK_PRIVE_ Store jp/konami/android/common/iab/KonamiIabBaseNativeActivity product_id 100BASE_FULL MOBILE enable_indicator_stats_for_game_mode grpc.max_concurrent_streams ca

OFFSET=0xa981f9 TERM=TURN
CONTEXT=t_permission NUM_NODES_END_MATCH LINK_TYPE RECEIVED_VOICE_DATA_COUNT_INMATCH MAIN_THREAD_ACTUAL_HZ_ PID MEMORY_VIRTUAL_PEAK_USED_KiB_ TURN_QUALITY_BASESESSION_TRANSPORT_RTT_COUNT LATENCY_TURN_GET_TURN_ADDRESS_MEAN MATCH_MOVE_INPUT_TIME_SEC TURN_UNKNOWN DCTEST_BEST_ROUTE_RESULT ABNORMALEND_REASON_FROM_SERVER OSVERSION LATENCY_MODE_MATCHING RTT_MEAN TRANSPORT_RTT_R_VARIANCE RSSI_R_MIN _CHCK_PRIVE_ Store jp/konami/android/common/iab/KonamiIabBaseNativeActivity product_id 100BASE_FULL MOBILE enable_indicator_stats_for_game_mode grpc.max_concurrent_streams call_->server_rpc_info() != nullptr Error %p i

OFFSET=0xa9a455 TERM=TURN
CONTEXT=nd CheckDemoTypeEnter CheckConditionSDConfigTag CheckOffsideGoal CheckDefenceCheckVariousDataForStealEvent CheckWinPointVariousData CheckMatchUpSituation SoundSpConditionFoul UniqueMotionKind ContactPlayVariousData FOOT_R POOR BALLOUT TOOK TURNOVER LANG_JPN CUT_TROPHY SCENE_ANTHEMEND AREA_AZ SIDE_LR BOUND RESTART_CK CUP_FRA_SP CUP_POR_SP LG_GER PLAYOFF_D3_JPN LG_ICC_AS YELLOWCARD NUM_SHOOT OVER_CENTERLINE SHOOT_FAILED WEIGHT RATIO_AT_RIGHT RATIO_STEAL_DEEP NUM_REVERSE OUT_LEFT ACTION GOAL_FRIEND LEAD_ADV FAMOUS NUM_CHEMISTRY 1STHALF_ONLY LEAGUE_2ND_SPLIT STAGE_4Q OF_FALSESB OFFENSE REASON_SHOOT AT

OFFSET=0xaa82f6 TERM=TURN
CONTEXT=_loop_front_back_3_3_near_gabriel autoMove_08_ragged45_slant_loop_2_2_STEP_near_gabriel dm_goal_extra_loop_0004 autoMove_00_bodyangle_00_135_00_3_3_STEP_near_gabriel autoMove_07_dribble_ragged45_front_loop_3_3_STEP_near_gabriel autoMove_35_TURNCANCEL_Back_3_3_f090_090_180_near_gabriel dash_08_dash_4_0_000_neardelay_Oriul dash_10_side_1_4_f045_dash_Oriul reaction_contact_0_3_090_act071_01 nearDefense_04_BODYTURN_Slant_3_3_f45_f90_f135_reverse_near_gabriel dribble_0_3_f180_y0_sole_act064 dm_oop_pointing_000_walk_1_1_walkback_135 StabilizerCam_corner_turn_2_L dm_oop_pointing_f045_runback_2_2 dm_oop_p

OFFSET=0xaa83a0 TERM=TURN
CONTEXT=Move_07_dribble_ragged45_front_loop_3_3_STEP_near_gabriel autoMove_35_TURNCANCEL_Back_3_3_f090_090_180_near_gabriel dash_08_dash_4_0_000_neardelay_Oriul dash_10_side_1_4_f045_dash_Oriul reaction_contact_0_3_090_act071_01 nearDefense_04_BODYTURN_Slant_3_3_f45_f90_f135_reverse_near_gabriel dribble_0_3_f180_y0_sole_act064 dm_oop_pointing_000_walk_1_1_walkback_135 StabilizerCam_corner_turn_2_L dm_oop_pointing_f045_runback_2_2 dm_oop_pointing_f135_walk_1_1 ActualBattle_181002_F100_t02_Gabriel F_ActualBattle_190123_K020_t01_Jua_02_Fcut002 ActualBattle_200127_F025_t02_Ortega enum_dummy24 new_dribblerun_3

OFFSET=0xaab52b TERM=TURN
CONTEXT=END_JOIN_USER_COMPE CmdGetUserBannerInfoList.php best_rank_vscom_league is_updated Settings/Support/MenuVoidMenu prechk_space.tmp ucasFileSize MemChange TaskEvCompeGetSchedule version_string Revision error [ m_maxSubstitutionsCount CMD_GET_TURN_SERVER_LIST ERR_CLIENT_UNKNOWN TaskUserActionGetGameplanInfo TaskSetAvatar 0000_f04_%d_ 0000_m05_%d_ Sombrero LongRangeShooting PenaltySpecialist ERR_GIVE_UP AddRequestHeader (Ljava/lang/String;Ljava/lang/String;)V application/octet-stream SetFileParam DcTestVer0 P2pModeTurnSendIntervalMs TurnEnableDualRouteModeTime TurnNetworkIoConnectionTimeoutMs TurnNe

OFFSET=0xaab982 TERM=TURN
CONTEXT=smatch. (error code = CMD_ALIGN_PROGRESS wait_other RP_NAT_TYPE UHP_FINALIZE_RET ALLOCATE RT_ACK | |->> [ %s ][ %04x ] %02X%02X%02X%02X EventSubURL NewLastConnectionError RemotePort ## Stun Status ${"rtt:":%d} CLASH E_CACHE_EXIST ALLOC_TURN_PERMISSION_BINDING_COMPLETE START_UDP_HOLE_PUNCHING_ABORTED STUN_PING_TIMEOUT HOST_DIRECT TARGET_CHAOS ED_UHP http://ntl.service.konami.net/ntl/api/GateInfo.php ios Ps4 out_of_play_timeout_sec out_of_play STANDARD_DEVIATION SERVNAMEV6_PEER SELF_AUTOMOVE_COUNT_BURST_L4 MATCH_CONTROL_SESSION_SEND_HEADER_SET_DELTATIME_FAIL_COUNT IP_ADDRESS_HOP_2_UDP_BEGIN_TEST

OFFSET=0xaabaef TERM=TURN
CONTEXT=.service.konami.net/ntl/api/GateInfo.php ios Ps4 out_of_play_timeout_sec out_of_play STANDARD_DEVIATION SERVNAMEV6_PEER SELF_AUTOMOVE_COUNT_BURST_L4 MATCH_CONTROL_SESSION_SEND_HEADER_SET_DELTATIME_FAIL_COUNT IP_ADDRESS_HOP_2_UDP_BEGIN_TEST TURN_QUALITY_BASE_RTT LATENCY_TURN_CONNECT_PEER_VARIANCE PING_LEVEL_SETTING INDICATOR_STATS_CSV LATENCY_MODE_ANNTENA_WAIT_QUALITY_CHECK V6_UDP_SOCKET_ERROR RSSI_R_MEAN getResponseCode getDescription getIntroductoryPrice getOfferToken getProduct Number of purchaseHistoryRecords: %d base_coin cmdName CmdSendTurnAddressData.php EHF TNL HOS grpc.enable_deadline_chec

OFFSET=0xaabb0d TERM=TURN
CONTEXT=teInfo.php ios Ps4 out_of_play_timeout_sec out_of_play STANDARD_DEVIATION SERVNAMEV6_PEER SELF_AUTOMOVE_COUNT_BURST_L4 MATCH_CONTROL_SESSION_SEND_HEADER_SET_DELTATIME_FAIL_COUNT IP_ADDRESS_HOP_2_UDP_BEGIN_TEST TURN_QUALITY_BASE_RTT LATENCY_TURN_CONNECT_PEER_VARIANCE PING_LEVEL_SETTING INDICATOR_STATS_CSV LATENCY_MODE_ANNTENA_WAIT_QUALITY_CHECK V6_UDP_SOCKET_ERROR RSSI_R_MEAN getResponseCode getDescription getIntroductoryPrice getOfferToken getProduct Number of purchaseHistoryRecords: %d base_coin cmdName CmdSendTurnAddressData.php EHF TNL HOS grpc.enable_deadline_checking xds_client compression op

OFFSET=0xaadfe9 TERM=TURN
CONTEXT=ALLSPEED NEAR_OUT ROOF FLOW_SET_BALL LEAGUE_2ND_PERIOD NUM_ELAPSED NUM_NOTLOSE_STREAK NUM_GOT_SCORE_STREAK CONCEDING_ALL PVPLEAGUE_RATING REASON_PASS TACTICAL_CHANGE REASON_CONTACT OUCH STAR_IN NUM_SAME_POS FATIGUE_OVER_DAMAGE 04A_DIRECT_RETURN_TO_CENTER RESULT_NEAR_MISS ACROBATIC_SHOOT CHASING MAZING_RUN ONE_KEEP_PL A1_PLAYER1 A1_LT_TFK A1_LT_TKO COMD_SET_POS CHANT_CALL_CK BGM_CALL_HOME_NATIONAL_ANTHEM FOUL_RESTART_END Rival Stadium_%d 40_MAIN Collabo_Test konamiCMPSetResource CheckAndShowCMP dt220 cpk_snd/xxx/ pad_ff_03 pad_ff_11 Init AssetPack status:%d [%s] AssetPack:%s download pending As

OFFSET=0xab31fb TERM=TURN
CONTEXT=irt_prop_compo m_spikeStainAlbedoTex PlayCursorOutAnimation GetIsGuideOn ECmnIconNominationType::TYPE_NOMINATION_4 ECmnIconStandardChanceDealType::TYPE_PV5 ECmnIconStandardChanceDealType::TYPE_PV3_OR_MORE ECommonWidgetLabelKind::FRAME_IN_RETURN ETeamType::TT_CLUB ETeamSideType::TST_HOME SkeletalMeshCrowd BottomLeftUV CustomStadiumAssetTableRow DemoCharacterRole::PLAYER CharacterRole EDemoShootingLocation::Default EventFlagChanged CameraNo pSorceWidget vec IsTouchStartMyself MorphConfidence CanDieCurrentWindow GetBgId skinTheme ELatestFadeKindEnum::LATEST_FADE_KIND_OUT_WIPE EFadeWipeKindEnum Entity

OFFSET=0xabb67d TERM=TURN
CONTEXT=40_circle_run_turn_2_2_mid_michael autoMove_40_circle_run_turn_3_3_mid_michael Slowerrun_3_0_045 avoidjumpsliding_3_4_000_high_act068_01 avoidjumpsliding_3_4_022_act068_03 autoMove_00_bodyangle_00_135_00_3_3_near_gabriel nearDefense_04_BODYTURN_Slant_1_1_rightfront_STEP_near_gabriel nearDefense_04_BODYTURN_Slant_1_1_rightside_STEP_near_gabriel gkblock_lie_s04_0_0_y04_090 nearDribble_04_1_dribble_burst_1_4_135_y0_oriul nearDribble_04_1_dribble_burst_1_4_f135_y0_oriul nearDribble_04_1_dribble_burst_0_4_045_y0_oriul tacklefoot_parallel_mid_0_0_f045_act064 feintrun_tap_3_3_f090_y0_sole_Ltouch_axisback

OFFSET=0xabb6bc TERM=TURN
CONTEXT=3_3_mid_michael Slowerrun_3_0_045 avoidjumpsliding_3_4_000_high_act068_01 avoidjumpsliding_3_4_022_act068_03 autoMove_00_bodyangle_00_135_00_3_3_near_gabriel nearDefense_04_BODYTURN_Slant_1_1_rightfront_STEP_near_gabriel nearDefense_04_BODYTURN_Slant_1_1_rightside_STEP_near_gabriel gkblock_lie_s04_0_0_y04_090 nearDribble_04_1_dribble_burst_1_4_135_y0_oriul nearDribble_04_1_dribble_burst_1_4_f135_y0_oriul nearDribble_04_1_dribble_burst_0_4_045_y0_oriul tacklefoot_parallel_mid_0_0_f045_act064 feintrun_tap_3_3_f090_y0_sole_Ltouch_axisbackin_act097 trap_0_3_f225_y0_in_act064 dm_oop_pointing_045_run_2_

OFFSET=0xabc141 TERM=TURN
CONTEXT= autoMove_00_01_gkmovenear_FrontBackLoop_slant_Angle5_1_1 autoMove_00_02_gkmovemid_FrontBackLoop_slant_Angle5_1_1 autoMove_00_gkmovenear_step_ChageAngle03_1_1 autoMove_00_gkmovenear_step_ChageAngle03_3_3 NEARKEEPER_04_02_gkmovenear_1_1_BODYTURN_SLANT NEARKEEPER_04_03_gkmovenear_3_3_BODYTURN_SLANT enum_dummy541 enum_dummy567 enum_dummy637 block_3_0_y00_f090_act071 gkmovenear_stopturn_2_0_v2 Project.hkx isRandomHandL base_d_end_banzai_hoe base_d_ent_warai base_g_catchs base_kuisibari_hard bitter_brwin_smirk_eyhc dml_neut_brwtrb_talk gk_brwup_puff_lith_fast neut_brwin_r neut_puck_mid neut_sbreth_arou

OFFSET=0xabc170 TERM=TURN
CONTEXT=Angle5_1_1 autoMove_00_02_gkmovemid_FrontBackLoop_slant_Angle5_1_1 autoMove_00_gkmovenear_step_ChageAngle03_1_1 autoMove_00_gkmovenear_step_ChageAngle03_3_3 NEARKEEPER_04_02_gkmovenear_1_1_BODYTURN_SLANT NEARKEEPER_04_03_gkmovenear_3_3_BODYTURN_SLANT enum_dummy541 enum_dummy567 enum_dummy637 block_3_0_y00_f090_act071 gkmovenear_stopturn_2_0_v2 Project.hkx isRandomHandL base_d_end_banzai_hoe base_d_ent_warai base_g_catchs base_kuisibari_hard bitter_brwin_smirk_eyhc dml_neut_brwtrb_talk gk_brwup_puff_lith_fast neut_brwin_r neut_puck_mid neut_sbreth_around pose_angry_talk_S_02 pose_neut_talk_03 pose_

OFFSET=0xabe865 TERM=TURN
CONTEXT=:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineMode\Task\Match\OnlineModeTaskSyncTeamSelect.cpp G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineMode\Task\Match\OnlineModeTaskSyncUserData.cpp CMD_AUTH_STEAM CMD_GET_TURN_ADDRESS_DATA CMD_SEND_TURN_ADDRESS_DATA CMD_SEND_VOICE_CHAT_DATA CMD_SET_KGS_PURCHASE_UNLOCKED %s_v3_m06 google_dma CommandApi UploadApi UNKNOWN VERSION: RecvMemory jp/konami/android/common/Cronet TxPpsRecentBasicStatisticsMaxSize BufferSizeLimitHigh ListenerWorkerThreadAffinityMask UEGameThreadAffinityMask AppYieldLowPriorityTimeoutMs OPPO/CPH2127|OPPO/CPH

OFFSET=0xabe880 TERM=TURN
CONTEXT=rce\Shared\pes\Game\Online\OnlineMode\Task\Match\OnlineModeTaskSyncTeamSelect.cpp G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineMode\Task\Match\OnlineModeTaskSyncUserData.cpp CMD_AUTH_STEAM CMD_GET_TURN_ADDRESS_DATA CMD_SEND_TURN_ADDRESS_DATA CMD_SEND_VOICE_CHAT_DATA CMD_SET_KGS_PURCHASE_UNLOCKED %s_v3_m06 google_dma CommandApi UploadApi UNKNOWN VERSION: RecvMemory jp/konami/android/common/Cronet TxPpsRecentBasicStatisticsMaxSize BufferSizeLimitHigh ListenerWorkerThreadAffinityMask UEGameThreadAffinityMask AppYieldLowPriorityTimeoutMs OPPO/CPH2127|OPPO/CPH2131|OPPO/CPH2133|OPPO/CPH2

OFFSET=0xabebe3 TERM=TURN
CONTEXT=pha ParityDecoderEnablePadding Mobility forbidden. (error code = CMD_MATCH_SETTINGS revision param_check_sum SIGN CHANNELBIND %s:%s:%s SCANNING WANIPv6FirewallControl relayedAddress ALLOC_CHNL E_INVALID_ARGS E_INVAL E_DUP_ENDPOINT REFRESH_TURN_PORT_ERROR ALLOC_TURN_PERMISSION_BINDING_ERROR FREE_TURN_PERMISSION_BINDING_ABORTED KEEP_UDP_HOLE_PUNCHING_ERROR retry_list use_static_session enable_happy_eyeballs wait_game_result_timeout_sec IDELAY_OVER_KEEP_BUF_SIZE_COUNT_MAX CONGESTION_CONTROL_WINDOW_SIZE_LIMIT_ MATCH_STOP_COUNT_BUF_EMPTY_BURST_L2 MATCH_STOP_COUNT_BUF_EMPTY_BURST_L4 MATCH_STOP_COUNT_SE

OFFSET=0xabebf9 TERM=TURN
CONTEXT=ePadding Mobility forbidden. (error code = CMD_MATCH_SETTINGS revision param_check_sum SIGN CHANNELBIND %s:%s:%s SCANNING WANIPv6FirewallControl relayedAddress ALLOC_CHNL E_INVALID_ARGS E_INVAL E_DUP_ENDPOINT REFRESH_TURN_PORT_ERROR ALLOC_TURN_PERMISSION_BINDING_ERROR FREE_TURN_PERMISSION_BINDING_ABORTED KEEP_UDP_HOLE_PUNCHING_ERROR retry_list use_static_session enable_happy_eyeballs wait_game_result_timeout_sec IDELAY_OVER_KEEP_BUF_SIZE_COUNT_MAX CONGESTION_CONTROL_WINDOW_SIZE_LIMIT_ MATCH_STOP_COUNT_BUF_EMPTY_BURST_L2 MATCH_STOP_COUNT_BUF_EMPTY_BURST_L4 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L3 

OFFSET=0xabec1c TERM=TURN
CONTEXT= code = CMD_MATCH_SETTINGS revision param_check_sum SIGN CHANNELBIND %s:%s:%s SCANNING WANIPv6FirewallControl relayedAddress ALLOC_CHNL E_INVALID_ARGS E_INVAL E_DUP_ENDPOINT REFRESH_TURN_PORT_ERROR ALLOC_TURN_PERMISSION_BINDING_ERROR FREE_TURN_PERMISSION_BINDING_ABORTED KEEP_UDP_HOLE_PUNCHING_ERROR retry_list use_static_session enable_happy_eyeballs wait_game_result_timeout_sec IDELAY_OVER_KEEP_BUF_SIZE_COUNT_MAX CONGESTION_CONTROL_WINDOW_SIZE_LIMIT_ MATCH_STOP_COUNT_BUF_EMPTY_BURST_L2 MATCH_STOP_COUNT_BUF_EMPTY_BURST_L4 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L3 MATCH_STOP_COUNT_BUF_EMPTY_BURST_L1

OFFSET=0xabeddf TERM=TURN
CONTEXT=MIT_ MATCH_STOP_COUNT_BUF_EMPTY_BURST_L2 MATCH_STOP_COUNT_BUF_EMPTY_BURST_L4 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L3 MATCH_STOP_COUNT_BUF_EMPTY_BURST_L1_MCACTIVE MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L5_MCACTIVE COMMUNICATION_TIME LATENCY_TURN_GET_TURN_ADDRESS_MAX GPU_MANUFACTURER NETWORKINFO EVENT_ID " getIntroductoryPriceCycles getItemDetails EMPTY_RECEIPT authorization_code CmdGetTurnAddressData.php M5 GDK getTxBytes grpc.http2_scheme grpc.keepalive_timeout_ms grpc.server_handshake_timeout_ms false && "It is illegal to call GetRecvMessage on a method which " "has a Cancel notification" %Y-%m-

OFFSET=0xabede8 TERM=TURN
CONTEXT=H_STOP_COUNT_BUF_EMPTY_BURST_L2 MATCH_STOP_COUNT_BUF_EMPTY_BURST_L4 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L3 MATCH_STOP_COUNT_BUF_EMPTY_BURST_L1_MCACTIVE MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L5_MCACTIVE COMMUNICATION_TIME LATENCY_TURN_GET_TURN_ADDRESS_MAX GPU_MANUFACTURER NETWORKINFO EVENT_ID " getIntroductoryPriceCycles getItemDetails EMPTY_RECEIPT authorization_code CmdGetTurnAddressData.php M5 GDK getTxBytes grpc.http2_scheme grpc.keepalive_timeout_ms grpc.server_handshake_timeout_ms false && "It is illegal to call GetRecvMessage on a method which " "has a Cancel notification" %Y-%m-%dT%H:%M:

OFFSET=0xace17f TERM=TURN
CONTEXT=toMove_03_crank90_loop_1_1_STEP_near_gabriel autoMove_06_zigzag135_side_loop_1_1_STEP_near_gabriel dm_goal_extra_loop_0003 dash_04_turn_4_4_045_CIRCLE_Oriul dash_09_idle_0_4_180_dash_Oriul dash_10_walk_1_4_180_dash_Oriul nearDefense_04_BODYTURN_Slant_1_1_f45_90_f135_reverse_near_gabriel nearDefense_04_BODYTURN_Slant_2_2_rightside_STEP_near_gabriel gkmovehigh_idle_0_0_180_ball gkcatchslideback_f01_3_0_y02_135 nearDribble_01_1_dribble_bodyfake_0_0_to_3_3_000_y0_gabriel nearDribble_04_1_dribble_burst_2_4_f090_y0_oriul dm_oop_lineup_f090_idle_0_1_walkside_090 tacklefoot_parallel_far_0_0_045_act095 tra

OFFSET=0xace1c2 TERM=TURN
CONTEXT=side_loop_1_1_STEP_near_gabriel dm_goal_extra_loop_0003 dash_04_turn_4_4_045_CIRCLE_Oriul dash_09_idle_0_4_180_dash_Oriul dash_10_walk_1_4_180_dash_Oriul nearDefense_04_BODYTURN_Slant_1_1_f45_90_f135_reverse_near_gabriel nearDefense_04_BODYTURN_Slant_2_2_rightside_STEP_near_gabriel gkmovehigh_idle_0_0_180_ball gkcatchslideback_f01_3_0_y02_135 nearDribble_01_1_dribble_bodyfake_0_0_to_3_3_000_y0_gabriel nearDribble_04_1_dribble_burst_2_4_f090_y0_oriul dm_oop_lineup_f090_idle_0_1_walkside_090 tacklefoot_parallel_far_0_0_045_act095 trap_0_3_f090_y3_in_act064 dml_goal_celebrate_0054 dml_goal_celebrate_

OFFSET=0xaceb72 TERM=TURN
CONTEXT=mmy350 enum_dummy355 LongVersion_201123_F025_t01_act071_01 LongVersion_201123_F027_t01_act071_02 enum_dummy394 ShortVersion_201123_F022_t01_act068_01 autoMove_00_01_gkmovemid_FrontBackLoop_step_Angle5_2_2 NEARKEEPER_04_02_gkmovemid_1_1_BODYTURN_SLANT autoMove_11_bodyangle_rolling_slow_3_3_Front_to_Back_mid enum_dummy465 enum_dummy508 enum_dummy510 enum_dummy526 enum_dummy540 enum_dummy565 enum_dummy566 enum_dummy621 enum_dummy646 block_neardelayside_2_0_y00_180_act071 defenseMove_01_parallel_4_3_neardelayback_act071 passGetMove_01_run_2_3_090_act071 gkrise_faceup_0_3_060 /Game/Assets/character/Dem

OFFSET=0xad1575 TERM=TURN
CONTEXT= NoMoveOperationTimeoutMs NtlApiThread %s%d REFLECTED_FROM TERM TRANSPORT | |->> [ %s ][ 0x%04x ] MappingTestIA urn:schemas-upnp-org:service:WANIPConnection:1 modelNumber </m:%s> }} ctxType ${"t":%d,"c":"%s","p":%d,"r":"%s","o":%d} ALLOC_TURN_PERMISSION_BINDING_ABORTED PEER_STUN REMOVE recieve_timeout_factor enable_sce_http2_error_reason_no_error_handling IPADDRV6 SEND_COMMAND_DROP_COUNT_BURST_L1_MCACTIVE SELF_AUTOMOVE_COUNT_BURST_L3 IP_ADDRESS_UDP_END_TEST MEMORY_PHYSICAL_PEAK_USED_KiB_ TURN_QUALITY_RTT_EWMA SEND_TO_NET_INFO_MAX_SEND_ATTEMPT_INTERVAL APP_YIELD_STATS_INACTIVITY_TIME_MS BPS_SEND_

OFFSET=0xad1674 TERM=TURN
CONTEXT=_BINDING_ABORTED PEER_STUN REMOVE recieve_timeout_factor enable_sce_http2_error_reason_no_error_handling IPADDRV6 SEND_COMMAND_DROP_COUNT_BURST_L1_MCACTIVE SELF_AUTOMOVE_COUNT_BURST_L3 IP_ADDRESS_UDP_END_TEST MEMORY_PHYSICAL_PEAK_USED_KiB_ TURN_QUALITY_RTT_EWMA SEND_TO_NET_INFO_MAX_SEND_ATTEMPT_INTERVAL APP_YIELD_STATS_INACTIVITY_TIME_MS BPS_SEND_ RX_LOSS_RATE_MEAN Not Implement <unsupported field> getQuantity getInventory xb1_store_id application_user_name CmdSendAuthorizationCode CmdGetTurnAddressData CmdSendAdjustParam LINK_DOWN AND grpc.max_connection_age_grace_ms grpc.max_metadata_size grpc.e

OFFSET=0xad6683 TERM=TURN
CONTEXT=d KEYFORMAT >= [netstm] Argument 'url' is empty. W202112272:The video pts discontinuity is detected but audio one is not. [IDR Seek] IDR seek finished: PTS: %lu, offset: %d, is_idr: %s, Target PTS: %lu CriAacdecAcodec failed. err=%d RETURN criAdo_DiscardSamples(%p, %ld, %ld). invalid frame id is selected. frame-rate Failed to call MediaCodec.flush() E2015040728:[CriVodStm] Media playlist is discard becuase it contains unsupported segment file. [CriVodStm] Could not get the media stream(%d) info. [vodstm] Failed to parse playlist. tsv criAesSegmentsDecryptor_Decrypt() failed. (nSrcSize=%u 

OFFSET=0xae169e TERM=TURN
CONTEXT=361 enum_dummy451 bench_sit_bend_backward bench_sit_think autoMove_00_01_gkmovemid_FrontBackLoop_slant_Angle5_3_3 autoMove_04_02_gkmovemid_Sidestep_Angle5_2_2 autoMove_08_01_gkmovenear_Sidestep_Angle5_1_1 NEARKEEPER_04_01_gkmovemid_1_1_BODYTURN_SLANT enum_dummy471 enum_dummy491 ShortVersion_201123_F003_t01_act071_02 ShortVersion_201123_F008_t01_act068_03 enum_dummy636 block_3_0_y01_f090_act080 defenseMove_01_parallel_3_4_act071 passGetMove_01_run_3_3_f270_act068 gkmovenear_sidestep_Chasing gkrise_sidewaysup_l_0_0_000 cpk_dat/common/anime/FoxAnim/Hand/CharacterAssets/pes_human_hand_200918.frig MtFi

OFFSET=0xae33ab TERM=TURN
CONTEXT=l_rank_list result_uniform_id DATA_PARAMETER_ST DATA_PARAMETER_BALL_SPIN_CONTROL DATA_PARAMETER_PLAYSTYLE DATA_PARAMETER_S_NON_ROTATING_SHOT DATA_PARAMETER_S_LOW_LOB DATA_PARAMETER_S_SOLE_CONTROL DATA_PARAMETER_S_IMPROVISER SKILL_CARD_EDGE_TURN ABILITY_SHORT_PASS ABILITY_WEAK_FOOT_ACCURACY BIRTH_DATE EULA_PRIVACY_NOTICE_KOREA TEAM_POWER_NONE MEASUREING LEAGUE_PRESET EVENT_THEME_CUSTOM TEAM_STYLE_POSSESSION SEASON_END TUTORIAL_MISSION_2 LIMIT_CLUB WAIT_OWNERS_START PLAYER_IN_OUT EX_PREPARE TRAINING_SKILL_STAR_PLAYER OPENING_SHOWTIME TOTAL_GOAL_CUSTOM_EVENT_COM SHOOT_CUSTOM_EVENT_PVP TOTAL_GET_MYLEA

OFFSET=0xae3e07 TERM=TURN
CONTEXT=schemas.xmlsoap.org/soap/envelope/"; ns=01 Content-Length: %d M-SEARCH * HTTP/1.1 HOST: [%s]:1900 MAN: "ssdp:discover" MX: %d ST: %s manufacturer <service> ControlURL natType UDHP E_CHAOS UPNP_RETREIVE_DEVICE_DESCRIPTION_ERROR FREE_TURN_PORT_ABORTED ALLOC_TURN_CHANNEL_BINDING_ERROR CHAOS DETECT_BAD canUseEthernet api_version ntl_impl_version users CONGESTION_CONTROL_BPS_ RECEIVED_FROM_UNKNOWN_PEER_COUNT RECEIVED_VOICE_DATA_LENGTH_INMATCH TURN_SESSION_RTT_COUNT P2PTURNIO_P2P_RX_LOSS_RATE LATENCY_TURN_GET_TURN_ADDRESS_MIN LATENCY_TURN_CONNECT_UDP_MAX SEND_TO_NET_INFO_MAX_SEND_INTERVAL SOC QU

OFFSET=0xae3e1f TERM=TURN
CONTEXT=/envelope/"; ns=01 Content-Length: %d M-SEARCH * HTTP/1.1 HOST: [%s]:1900 MAN: "ssdp:discover" MX: %d ST: %s manufacturer <service> ControlURL natType UDHP E_CHAOS UPNP_RETREIVE_DEVICE_DESCRIPTION_ERROR FREE_TURN_PORT_ABORTED ALLOC_TURN_CHANNEL_BINDING_ERROR CHAOS DETECT_BAD canUseEthernet api_version ntl_impl_version users CONGESTION_CONTROL_BPS_ RECEIVED_FROM_UNKNOWN_PEER_COUNT RECEIVED_VOICE_DATA_LENGTH_INMATCH TURN_SESSION_RTT_COUNT P2PTURNIO_P2P_RX_LOSS_RATE LATENCY_TURN_GET_TURN_ADDRESS_MIN LATENCY_TURN_CONNECT_UDP_MAX SEND_TO_NET_INFO_MAX_SEND_INTERVAL SOC QUALITY_SETTING_FOR_STADIU

OFFSET=0xae3ed9 TERM=TURN
CONTEXT=DEVICE_DESCRIPTION_ERROR FREE_TURN_PORT_ABORTED ALLOC_TURN_CHANNEL_BINDING_ERROR CHAOS DETECT_BAD canUseEthernet api_version ntl_impl_version users CONGESTION_CONTROL_BPS_ RECEIVED_FROM_UNKNOWN_PEER_COUNT RECEIVED_VOICE_DATA_LENGTH_INMATCH TURN_SESSION_RTT_COUNT P2PTURNIO_P2P_RX_LOSS_RATE LATENCY_TURN_GET_TURN_ADDRESS_MIN LATENCY_TURN_CONNECT_UDP_MAX SEND_TO_NET_INFO_MAX_SEND_INTERVAL SOC QUALITY_SETTING_FOR_STADIUM DOWNLOAD_SERVER_STATS_URL LATENCY_MODE_CONFIRMING_RESULT MEMPEAK_FLOW_HASH -o Source\Shared\pes\Game\Online\OnlineSystem\ServerDef\OnlineSystemServerKeywordDef.h CAMPAIGN getOriginalP

OFFSET=0xae3ef3 TERM=TURN
CONTEXT=REE_TURN_PORT_ABORTED ALLOC_TURN_CHANNEL_BINDING_ERROR CHAOS DETECT_BAD canUseEthernet api_version ntl_impl_version users CONGESTION_CONTROL_BPS_ RECEIVED_FROM_UNKNOWN_PEER_COUNT RECEIVED_VOICE_DATA_LENGTH_INMATCH TURN_SESSION_RTT_COUNT P2PTURNIO_P2P_RX_LOSS_RATE LATENCY_TURN_GET_TURN_ADDRESS_MIN LATENCY_TURN_CONNECT_UDP_MAX SEND_TO_NET_INFO_MAX_SEND_INTERVAL SOC QUALITY_SETTING_FOR_STADIUM DOWNLOAD_SERVER_STATS_URL LATENCY_MODE_CONFIRMING_RESULT MEMPEAK_FLOW_HASH -o Source\Shared\pes\Game\Online\OnlineSystem\ServerDef\OnlineSystemServerKeywordDef.h CAMPAIGN getOriginalPrice ()Lcom/android/billin

OFFSET=0xae3f13 TERM=TURN
CONTEXT=_CHANNEL_BINDING_ERROR CHAOS DETECT_BAD canUseEthernet api_version ntl_impl_version users CONGESTION_CONTROL_BPS_ RECEIVED_FROM_UNKNOWN_PEER_COUNT RECEIVED_VOICE_DATA_LENGTH_INMATCH TURN_SESSION_RTT_COUNT P2PTURNIO_P2P_RX_LOSS_RATE LATENCY_TURN_GET_TURN_ADDRESS_MIN LATENCY_TURN_CONNECT_UDP_MAX SEND_TO_NET_INFO_MAX_SEND_INTERVAL SOC QUALITY_SETTING_FOR_STADIUM DOWNLOAD_SERVER_STATS_URL LATENCY_MODE_CONFIRMING_RESULT MEMPEAK_FLOW_HASH -o Source\Shared\pes\Game\Online\OnlineSystem\ServerDef\OnlineSystemServerKeywordDef.h CAMPAIGN getOriginalPrice ()Lcom/android/billingclient/api/ProductDetails$Prici

OFFSET=0xae3f1c TERM=TURN
CONTEXT=BINDING_ERROR CHAOS DETECT_BAD canUseEthernet api_version ntl_impl_version users CONGESTION_CONTROL_BPS_ RECEIVED_FROM_UNKNOWN_PEER_COUNT RECEIVED_VOICE_DATA_LENGTH_INMATCH TURN_SESSION_RTT_COUNT P2PTURNIO_P2P_RX_LOSS_RATE LATENCY_TURN_GET_TURN_ADDRESS_MIN LATENCY_TURN_CONNECT_UDP_MAX SEND_TO_NET_INFO_MAX_SEND_INTERVAL SOC QUALITY_SETTING_FOR_STADIUM DOWNLOAD_SERVER_STATS_URL LATENCY_MODE_CONFIRMING_RESULT MEMPEAK_FLOW_HASH -o Source\Shared\pes\Game\Online\OnlineSystem\ServerDef\OnlineSystemServerKeywordDef.h CAMPAIGN getOriginalPrice ()Lcom/android/billingclient/api/ProductDetails$PricingPhases;

OFFSET=0xae3f35 TERM=TURN
CONTEXT=T_BAD canUseEthernet api_version ntl_impl_version users CONGESTION_CONTROL_BPS_ RECEIVED_FROM_UNKNOWN_PEER_COUNT RECEIVED_VOICE_DATA_LENGTH_INMATCH TURN_SESSION_RTT_COUNT P2PTURNIO_P2P_RX_LOSS_RATE LATENCY_TURN_GET_TURN_ADDRESS_MIN LATENCY_TURN_CONNECT_UDP_MAX SEND_TO_NET_INFO_MAX_SEND_INTERVAL SOC QUALITY_SETTING_FOR_STADIUM DOWNLOAD_SERVER_STATS_URL LATENCY_MODE_CONFIRMING_RESULT MEMPEAK_FLOW_HASH -o Source\Shared\pes\Game\Online\OnlineSystem\ServerDef\OnlineSystemServerKeywordDef.h CAMPAIGN getOriginalPrice ()Lcom/android/billingclient/api/ProductDetails$PricingPhases; getPurchaseTime getRecei

OFFSET=0xae655f TERM=TURN
CONTEXT=ent. Error null (0) or unexpected EOF found in input stream. Converted Convert CheckAbilityValueDetail CheckCollaboEventData CheckDiffTwoAngles CheckCounterData FeintKind AreaList CompeName SetPlayKind SoundTargetSp SubstitutionVariousData TURNEND FRONT KNOCKOUT_ROUND_QFINAL KNOCKOUT_ROUND_TO_FINAL LANG_MEX SCENE_TO_MATCH RANGE_ENTRY FLY 3RD_QUALIFY QUALIFY_PLAYOFF CUP_EURO CUP_CHL_SP LG_SPA1 LG_NET DRIBBLE_SUCCESS SET_FK SET_KICKOFF_HALF LINKAGE_L_PASSER WEAK_FOOT_ACCURACY TOO_LONG OUT_UP THROWAWAY_UP SA_TV1 FLOW_RESULT_SHOOT KIND_HALFTIME NUM_SEC_REMAIN_CUT GOLAZO NET_DEFENCE ENTERDEMO CUP_PRE_K

OFFSET=0xaf40d4 TERM=TURN
CONTEXT=_act068_01 autoMove_02_reverse_stop_front_back_2_2_STEP_near_gabriel autoMove_07_ragged45_front_loop_1_1_STEP_near_gabriel autoMove_08_dribble_ragged45_slant_loop_2_2_STEP_near_gabriel autoMove_32_dribble_go_to_1_1_near_gabriel autoMove_35_TURNCANCEL_long_Front_3_3_f135_f180_near_gabriel nearDribble_04_1_dribble_burst_1_4_045_y0_oriul new_dribblerun_2_3_f135_y0_sole_act064 dm_miss_jog_2_1_walk_repent_180 dm_miss_run_3_1_walk_repent_135 js_parallel_interrupt_000_set01_4_4_000_of_act097 tacklefoot_sideways_near_0_0_f045_act095 gknearmovestep_fast_side_0_3 dml_goal_celebrate_0114 dml_goal_celebrate_0

OFFSET=0xaf4a79 TERM=TURN
CONTEXT=_dummy444 bench_sit_hold_head bench_sit_normal autoMove_00_01_gkmovemid_FrontBackLoop_slant_Angle5_1_1 autoMove_00_01_gkmovemid_FrontBackLoop_step_Angle5_3_3 autoMove_07_01_gkmovenear_Sidestep_Angle5_1_1 NEARKEEPER_04_01_gkmovenear_1_1_BODYTURN_SLANT enum_dummy468 enum_dummy486 enum_dummy498 enum_dummy607 enum_dummy627 gkrise_faceup_0_3_180 LongVersion_161108_F100_t01_Michael_03 sourceEndFrame angry_talk_L_02 angr_brwnit_shut_hard base_head_hit base_syucyu_iki_soft head_brwup_mso_eyc neut_breth_watch neut_mso pose_sorrow_dejection_M_04 pose_sorrow_pain_grit_01 smile_photo_01 song_bra_Loud_around c

OFFSET=0xaf745b TERM=TURN
CONTEXT=r RemoteHost InternalClient GetSpecificPortMappingEntry tcp ## AppInfo ${"%s":"%s"} ${"%s":"%s"} ${"%s":"%s"} ${"%s":"%s"} ${"%s":%d} ${"%s":%d} ${"%s":%d} ${"%s":"%s:%d"} %d_%08x%08x%08x%08x_%04x API_STATUS PUT_LOG_URL E_UNKNOWN REFRESH_TURN_PORT_COMPLETE record_limit error_list pCommand [0x Def_Online_Use_parallel_download timeout_settings match_session_disconneted_timeout_sec HOP_COUNT_ICMP_END_TEST RX_PPS_ SEND_COMMAND_DROP_COUNT_BURST_L3 SEND_COMMAND_DROP_COUNT_BURST_L2_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L3 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L4_MCACTIVE TX_BPS_ IP_ADDRESS_UDP_BEGI

OFFSET=0xaf75d6 TERM=TURN
CONTEXT=_sec HOP_COUNT_ICMP_END_TEST RX_PPS_ SEND_COMMAND_DROP_COUNT_BURST_L3 SEND_COMMAND_DROP_COUNT_BURST_L2_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L3 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L4_MCACTIVE TX_BPS_ IP_ADDRESS_UDP_BEGIN_TEST LATENCY_TURN_RESOLVING_NAME_VARIANCE LATENCY_TURN_CONNECT_UDP_MEAN MATCH_CATEGORY VSYNC_INTERVAL CS_SERVER_REGION LATENCY_MODE_PRE_MENU LATENCY_MODE_MATCHING_POLLING_CMD_GET_MATCHING_RESULT SURVEY_ID_1 RX_LOSS_RATE_R_MEAN _REQ_ acknowledgePurchase nativeOnGetItemDetailsFinished CmdCheckString.php CmdSendAuthorizationCode.php server_certificate_data_size CmdWatchInvitati

OFFSET=0xaf75fb TERM=TURN
CONTEXT=SEND_COMMAND_DROP_COUNT_BURST_L3 SEND_COMMAND_DROP_COUNT_BURST_L2_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L3 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L4_MCACTIVE TX_BPS_ IP_ADDRESS_UDP_BEGIN_TEST LATENCY_TURN_RESOLVING_NAME_VARIANCE LATENCY_TURN_CONNECT_UDP_MEAN MATCH_CATEGORY VSYNC_INTERVAL CS_SERVER_REGION LATENCY_MODE_PRE_MENU LATENCY_MODE_MATCHING_POLLING_CMD_GET_MATCHING_RESULT SURVEY_ID_1 RX_LOSS_RATE_R_MEAN _REQ_ acknowledgePurchase nativeOnGetItemDetailsFinished CmdCheckString.php CmdSendAuthorizationCode.php server_certificate_data_size CmdWatchInvitation invitation_task getRxBytes grpc.ce

OFFSET=0xb07179 TERM=TURN
CONTEXT=bble_bodyangle_00_90_00_2_2_STEP_near_gabriel autoMove_01_dribble_reverse_loop_side_3_3_STEP_near_gabriel autoMove_05_dribble_zigzag135_front_loop_2_2_STEP_near_gabriel ballTouch_05_5_dribble_touch_far_1_1_000_y0_gabriel nearDefense_04_BODYTURN_Slant_2_2_rightfront_STEP_near_gabriel autoMove_02_dribble_reverse_stop_rightfront_leftback_1_1_STEP_near_gabriel gkmovehigh_idle_0_0_135_ball feint_springturn_0_3_f067_y0_in_out_act097 dml_goal_celebrate_0279 js_run_dodge_045_set01_3_3_135_df_act064 js_run_interrupt_000_set01_3_3_000_of_act097 dm_oop_ballcome_handup_double_f090_walk_1_1_side_000 gknearmove

OFFSET=0xb07af7 TERM=TURN
CONTEXT=ersion_201123_F018_t01_act068_01 LongVersion_201123_F024_t01_act071_02 LongVersion_201123_F029_t01_act068_01 LongVersion_201124_F032_t01_act071_02 enum_dummy459 autoMove_33_01_gkmovenear_idle_idleturn_0_0 NEARKEEPER_04_03_gkmovemid_2_2_BODYTURN_SLANT NEARKEEPER_04_04_gkmovemid_3_3_BODYTURN_SLANT autoMove_11_bodyangle_rolling_slow_3_3_Back_to_Front_mid_michael enum_dummy482 enum_dummy522 enum_dummy538 enum_dummy569 enum_dummy573 ShortVersion_201123_F004_t01_act068_01 enum_dummy603 ShortVersion_201123_F016_t01_act071_01 enum_dummy652 defenseMove_01_parallel_4_3_f270_act068_02 enum_dummy657 cpk_dat/c

OFFSET=0xb07b25 TERM=TURN
CONTEXT=01123_F024_t01_act071_02 LongVersion_201123_F029_t01_act068_01 LongVersion_201124_F032_t01_act071_02 enum_dummy459 autoMove_33_01_gkmovenear_idle_idleturn_0_0 NEARKEEPER_04_03_gkmovemid_2_2_BODYTURN_SLANT NEARKEEPER_04_04_gkmovemid_3_3_BODYTURN_SLANT autoMove_11_bodyangle_rolling_slow_3_3_Back_to_Front_mid_michael enum_dummy482 enum_dummy522 enum_dummy538 enum_dummy569 enum_dummy573 ShortVersion_201123_F004_t01_act068_01 enum_dummy603 ShortVersion_201123_F016_t01_act071_01 enum_dummy652 defenseMove_01_parallel_4_3_f270_act068_02 enum_dummy657 cpk_dat/common/anime/FoxAnim/Hand/CharacterAssets/hand_

OFFSET=0xb09a4f TERM=TURN
CONTEXT=count_limit target_id world_distribution_list special_emblem_name time_limit_for_next_match match_result_list DATA_PARAMETER_RMF DATA_PARAMETER_LONG_PASS DATA_PARAMETER_RUNNING_POSTURE DATA_PARAMETER_PENALTY_KICK_TYPE DATA_PARAMETER_S_EDGE_TURN DATA_PARAMETER_S_SLIDING PLAY_STYLE_LINE_BREAKER PLAY_STYLE_CHANCE_GETTER ABILITY_BALL_SPIN_CONTROL FRIEND_MATCH TEAM_POWER_LV4 TEAM_POWER_NO_LIMIT LOBBY_ROOM_MATCH_3VSCOM LEAGUE_CUSTOM LEAGUE_PRESET_TEAM CONDITION_NORMAL OFFENSIVE ABILITY_TRAINING_SELECT CUSTOM_RANKING AGENT_CONFIRMED_RARE SHOW_ANNOUNCE_VIEW ACHIEVE_HAT_TRICK MATCH_LOSE SPECIAL_PLAYER HALF

OFFSET=0xb0ceb3 TERM=TURN
CONTEXT=ta EndDemoStatus CHANGE_IN EDIT_NG BGM_EXIST_COMPE FIELD_OUT FIELD_PENALTY TO_LEFT CUP_PEU CUP_PAS LG_COL CUP_JPN_EMPEROR NUM_LAST_MOVEX NUM_TIMER NUM_FRIEND_FREE STOP_CLEAR HEADING MAYBE_GET SAME_TEAM CALL REPEATABLE FLOW_MAIN_SETTING NUM_TURN KIND_RETIRE_BL IS_SFINAL KIND_NATIONAL EXTIME NUM_LOSE_STREAK OF_WIDE BIGTIME IS_ACHIEVE PRE_RESULT_DEFLECTION OUTOF_PASS_TARGET FLIP_FLAP_SKILLS NO_LOOK_PASS HIGH_PUNT_KICK GAME_CHANGING_PASS VISIONARY_PASS LONG_RANGE A1_TEAMVS1 BGM_STOP_ENTER_ETC /common/sound/match/CheersBranchName.bin SOUNDSYS_LOAD SMALL_HOME SS_MasterOut_MuteON cpk_snd/common/sound/mat

OFFSET=0xb1a62d TERM=TURN
CONTEXT=e_01_reverse_loop_front_back_1_1_STEP_near_gabriel autoMove_02_reverse_stop_leftfront_rightback_2_2_STEP_near_gabriel autoMove_03_dribble_crank90_loop_3_3_STEP_near_gabriel autoMove_04_dribble_crank45_loop_2_2_STEP_near_gabriel autoMove_35_TURNCANCEL_long_Front_3_3_f045_f090_near_gabriel dash_10_side_1_4_f135_dash_Oriul dash_10_side_1_4_f180_dash_Oriul reaction_contact_0_2_135_act071_01 autoMove_02_dribble_reverse_stop_front_back_2_2_STEP_near_gabriel nearDribble_04_1_dribble_burst_2_4_f045_y0_oriul nearDribble_02_2_dribble_elastico_0_1_to_3_3_000_y0_take3_gabriel gkgoalkick_Quick_short_0_0_090_ri

OFFSET=0xb1d426 TERM=TURN
CONTEXT=mRecordList BNR PIF AGT %08llu StyleValue TaskGetRequestedJoinUserCompeInfo tag_createjoinRoom TaskLoginSubEula TaskLoginCheckGameMode match TaskSyncCoopPlayerData TaskRecvCampaignPassReward CommandErrorManager ERR_CLIENT_TIMEOUT CMD_WATCH_TURN_ADDRESS_DATA _lim 03 07 17 26 jp/konami/android/common/HttpImpl RxRecentlyPacketLossRateRecentBasicStatisticsMaxSize SendBufferLimitRateHigh LatencyWarningLv2ConditionQueueingSizeThreshold BufferLimitRateHigh CorrectionRiseThresholdLow CorrectionRiseWaitTimeMsThresholdLow CorrectionRiseDeterminationNotReadyForCommandDeltaCountThresholdHigh NetworkQualityInd

OFFSET=0xb1d7a7 TERM=TURN
CONTEXT=REQUESTED_TRANSPORT DONT_FRAGMENT ATTR_EXTENSION O573_ID REFRESH CONNECTIONATTEMPT MappingTestIF ChannelRefresh NOT_SCANNED "upnpVersion":"%d.%d" NewExternalPort locale E_NOINIT E_NOROUTE E_MSGBROKEN UPNP_ADD_PORT_FORWARDING_COMPLETE ALLOC_TURN_PORT_AUTH_ERROR START_UDP_HOLE_PUNCHING_TRANSPORT_FINALIZE ConnectionManager xb1 get_game_result_timeout_sec NUM_LOCAL_GUESTS_END_MATCH HOP_COUNT_UDP_BEGIN_TEST MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L2_MCACTIVE IP_ADDRESS_HOP_1_UDP_BEGIN_TEST MEMORY_TOTAL_KiB MEMORY_VIRTUAL_USED_KiB_ IS_PK MATCH_SETTING_WEATHER LATENCY_TURN_RESOLVING_NAME_ANY_MIN DCTEST_DET

OFFSET=0xb1d8ed TERM=TURN
CONTEXT=get_game_result_timeout_sec NUM_LOCAL_GUESTS_END_MATCH HOP_COUNT_UDP_BEGIN_TEST MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L2_MCACTIVE IP_ADDRESS_HOP_1_UDP_BEGIN_TEST MEMORY_TOTAL_KiB MEMORY_VIRTUAL_USED_KiB_ IS_PK MATCH_SETTING_WEATHER LATENCY_TURN_RESOLVING_NAME_ANY_MIN DCTEST_DETAIL_INFO GPU BACKGROUND_MS_LIST CS_SERVER_REGION_PRIORITY GAME_SERVER_NAME DOWNLOAD_SERVER_STATS_SEND_URL GAME_SERVER_STATS_RECV_URL inapp getSubscriptionPeriod getPurchaseState getObfuscatedAccountId nativeOnConsumeFinished limit_buy_count enable_dual_price_system tls_port ConnectTurnTask FIREWIRE getRssi (Landroid/content/

OFFSET=0xb2e003 TERM=TURN
CONTEXT=364 enum_dummy383 enum_dummy391 enum_dummy437 bench_sit_bend_forward autoMove_03_01_gkmovemid_Sidestep_Angle5_3_3 autoMove_05_01_gkmovemid_Sidestep_Angle5_2_2 autoMove_07_02_gkmovenear_Sidestep_Angle5_2_2 NEARKEEPER_04_01_gkmovemid_3_3_BODYTURN_SLANT NEARKEEPER_04_01_gkmovenear_3_3_BODYTURN_SLANT NEARKEEPER_04_02_gkmovenear_2_2_BODYTURN_SLANT NEARKEEPER_04_03_gkmovenear_1_1_BODYTURN_SLANT enum_dummy462 enum_dummy493 enum_dummy515 ShortVersion_201123_F008_t01_act068_01 ShortVersion_201123_F014_t01_act068_02 fadeOut isReferenced base_d_card_warai base_d_end_photo_hoe base_g_shoot_kuisibari loss_brwt

OFFSET=0xb2e032 TERM=TURN
CONTEXT=ench_sit_bend_forward autoMove_03_01_gkmovemid_Sidestep_Angle5_3_3 autoMove_05_01_gkmovemid_Sidestep_Angle5_2_2 autoMove_07_02_gkmovenear_Sidestep_Angle5_2_2 NEARKEEPER_04_01_gkmovemid_3_3_BODYTURN_SLANT NEARKEEPER_04_01_gkmovenear_3_3_BODYTURN_SLANT NEARKEEPER_04_02_gkmovenear_2_2_BODYTURN_SLANT NEARKEEPER_04_03_gkmovenear_1_1_BODYTURN_SLANT enum_dummy462 enum_dummy493 enum_dummy515 ShortVersion_201123_F008_t01_act068_01 ShortVersion_201123_F014_t01_act068_02 fadeOut isReferenced base_d_card_warai base_d_end_photo_hoe base_g_shoot_kuisibari loss_brwtrb_talk_blin neut_bite_01 neut_breath_short_gk_

OFFSET=0xb2e061 TERM=TURN
CONTEXT=Sidestep_Angle5_3_3 autoMove_05_01_gkmovemid_Sidestep_Angle5_2_2 autoMove_07_02_gkmovenear_Sidestep_Angle5_2_2 NEARKEEPER_04_01_gkmovemid_3_3_BODYTURN_SLANT NEARKEEPER_04_01_gkmovenear_3_3_BODYTURN_SLANT NEARKEEPER_04_02_gkmovenear_2_2_BODYTURN_SLANT NEARKEEPER_04_03_gkmovenear_1_1_BODYTURN_SLANT enum_dummy462 enum_dummy493 enum_dummy515 ShortVersion_201123_F008_t01_act068_01 ShortVersion_201123_F014_t01_act068_02 fadeOut isReferenced base_d_card_warai base_d_end_photo_hoe base_g_shoot_kuisibari loss_brwtrb_talk_blin neut_bite_01 neut_breath_short_gk_saving_S_02 pose_angry_S_05 pose_neut_purse_one

OFFSET=0xb2e090 TERM=TURN
CONTEXT=destep_Angle5_2_2 autoMove_07_02_gkmovenear_Sidestep_Angle5_2_2 NEARKEEPER_04_01_gkmovemid_3_3_BODYTURN_SLANT NEARKEEPER_04_01_gkmovenear_3_3_BODYTURN_SLANT NEARKEEPER_04_02_gkmovenear_2_2_BODYTURN_SLANT NEARKEEPER_04_03_gkmovenear_1_1_BODYTURN_SLANT enum_dummy462 enum_dummy493 enum_dummy515 ShortVersion_201123_F008_t01_act068_01 ShortVersion_201123_F014_t01_act068_02 fadeOut isReferenced base_d_card_warai base_d_end_photo_hoe base_g_shoot_kuisibari loss_brwtrb_talk_blin neut_bite_01 neut_breath_short_gk_saving_S_02 pose_angry_S_05 pose_neut_purse_one_lips_02 pose_sorrow_pain_grit_02 smil_smirk_so

OFFSET=0xb30855 TERM=TURN
CONTEXT=ory_key ACTIVENETWORK:ETHERNET XOR_MAPPED_ADDRESS_3489 RP_AMF_DATA PAD16 REF_ADDR ERROR_RESP MappingTestIII M-SEARCH * HTTP/1.1 HOST: %s:1900 MAN: "ssdp:discover" MX: %d ST: %s },"service":[ LeaseTime ERROR_DISCONNECTED BAD_ROUTE E_TURN_AUTH_ERROR UPNP_QUERY_DEVICE_STATUS_ERROR FREE_TURN_CHANNEL_BINDING_ERROR STOP_UDP_HOLE_PUNCHING_COMPLETE ntl_check_v4_nat_possible ForceDisconnect: %02d/%02d[%02d:%02d:%02d.%03d](%02d:%02d:%02d) giveup_msec nio system in_play SERVNAME NATTYPEV6_PEER COMMUNICATION_MODE RX_LOSS_RATE_ SEND_COMMAND_DROP_COUNT_BURST_L1 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L3_M

OFFSET=0xb30889 TERM=TURN
CONTEXT=89 RP_AMF_DATA PAD16 REF_ADDR ERROR_RESP MappingTestIII M-SEARCH * HTTP/1.1 HOST: %s:1900 MAN: "ssdp:discover" MX: %d ST: %s },"service":[ LeaseTime ERROR_DISCONNECTED BAD_ROUTE E_TURN_AUTH_ERROR UPNP_QUERY_DEVICE_STATUS_ERROR FREE_TURN_CHANNEL_BINDING_ERROR STOP_UDP_HOLE_PUNCHING_COMPLETE ntl_check_v4_nat_possible ForceDisconnect: %02d/%02d[%02d:%02d:%02d.%03d](%02d:%02d:%02d) giveup_msec nio system in_play SERVNAME NATTYPEV6_PEER COMMUNICATION_MODE RX_LOSS_RATE_ SEND_COMMAND_DROP_COUNT_BURST_L1 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L3_MCACTIVE MEMORY_PHYSICAL_AVAILABLE_KiB_ MEMORY_PHYSIC

OFFSET=0xb30a05 TERM=TURN
CONTEXT=2d:%02d) giveup_msec nio system in_play SERVNAME NATTYPEV6_PEER COMMUNICATION_MODE RX_LOSS_RATE_ SEND_COMMAND_DROP_COUNT_BURST_L1 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L3_MCACTIVE MEMORY_PHYSICAL_AVAILABLE_KiB_ MEMORY_PHYSICAL_USED_KiB_ P2PTURNIO_TURN_RTT_MIN HTTP_WAITFORCONNECTIVITY RSSI_MIN RX_LOSS_RATE_MIN RX_LOSS_RATE_R_VARIANCE CmdGetProductList getProductType getSubscriptionOfferDetails getObfuscatedProfileId restartConnection canMakePayment can_buy_count pid_list retry_cmd_server_list SignInCheckTask GetModelName grpc.http2.initial_sequence_number grpc.workaround.cronet_compression ops_ sta

OFFSET=0xb30a0c TERM=TURN
CONTEXT=) giveup_msec nio system in_play SERVNAME NATTYPEV6_PEER COMMUNICATION_MODE RX_LOSS_RATE_ SEND_COMMAND_DROP_COUNT_BURST_L1 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L3_MCACTIVE MEMORY_PHYSICAL_AVAILABLE_KiB_ MEMORY_PHYSICAL_USED_KiB_ P2PTURNIO_TURN_RTT_MIN HTTP_WAITFORCONNECTIVITY RSSI_MIN RX_LOSS_RATE_MIN RX_LOSS_RATE_R_VARIANCE CmdGetProductList getProductType getSubscriptionOfferDetails getObfuscatedProfileId restartConnection canMakePayment can_buy_count pid_list retry_cmd_server_list SignInCheckTask GetModelName grpc.http2.initial_sequence_number grpc.workaround.cronet_compression ops_ started_ f

OFFSET=0xb41024 TERM=TURN
CONTEXT=_t01_act068_01 enum_dummy378 enum_dummy407 enum_dummy418 enum_dummy438 autoMove_00_gkmovemid_step_ChageAngle01_3_3 autoMove_00_gkmovemid_step_ChageAngle02_1_1 autoMove_08_01_gkmovemid_Sidestep_Angle5_2_2 NEARKEEPER_04_05_gkmovenear_1_1_BODYTURN_SLANT enum_dummy504 enum_dummy514 enum_dummy572 enum_dummy574 enum_dummy606 enum_dummy615 enum_dummy620 defenseMove_01_neardelayback_3_4_parallel_act068 passGetMove_01_run_3_3_f180_act068 gkrise_sidewaysStephead_l_0_3_000_hand LongVersion_201123_F030_t03_act068_02 Ball Person 01 hitFrames ef23_protest_strong head_brwup_mho_eyc neut_breath_S_01 neut_breth_ey

OFFSET=0xb41690 TERM=TURN
CONTEXT=ed with %ld bytes remaining to read Clear auth, redirects to port from %u to %u mqtt No MQTT topic found. Forgot to URL encode it? localhost/ pop3 /.. SSL-PROXY ALPN: server accepted %.*s Supplemental data RSA Public Key p SSL_ERROR_ZERO_RETURN ALPN: curl offers %s OpenSSL SSL_read: %s, errno %d curl_ws_recv, added %zu bytes from network WS: unaligned frame size (sending %zu instead of %ld) NON-FIN debug ObjectDesc ClothHConstraintParam COMMAND DEMO_CONTROL NO_OPERATION_LEAVE DevelopData/common/match/constant/ballPerson/ball_person_st042.json DevelopData/common/match/constant/ballPerson/ball_pers

OFFSET=0xb429cc TERM=TURN
CONTEXT= CENTERING_GET FALL_DOWN SEAMLESS_CORNERKICK DEMO_GOALEVENT DEMO_GOALEVENT_FINISH_ACTION PASS_RESULT_SITUATION_SUCCESS LOOSEBALL_ATTACK LINEOUT BACKHEAD ANIME_KICKOFF_RECEIVER_LOOP ANIME_KP_CATCH FEINT_KIND_SEMIAUTO_BACK FEINT_KIND_ELASTICOTURN_R FEINT_KIND_DOUBLETOUCH_SCISSORS_L CANCEL TUTORIAL_RESTART_KIND_THROW_IN SUGOROKU_OBJECT_KIND_DUMMY_BRIDGE_X3 cpk_dat/common/match/tutorial_replay/tutorial_replay_through_pass_02.trep cpk_dat/common/match/tutorial_replay/tutorial_replay_sliding_03.rep cpk_dat/common/match/tutorial_replay/tutorial_replay_clearing_02.rep CmdCheckUserDelete Birthday MenuEvCom

OFFSET=0xb43b5e TERM=TURN
CONTEXT=FIDIRECTLAN_LOW_LEVEL P2P_ADHOC_LAN direct_online_turn_mode NetworkQualityIndicator ps f2p RESPONSE_ADDRESS RP_SYNC_POINT |->> [ %s ][ %d ] URLBase TurnInitializedNatType RevokeConnectivity uds E_NOMEM E_NOTFOUND E_UPNP_DEVICE_NOT_FOUND E_TURN_NOT_AVAILABLE UPNP_DISCOVERY_FULL_COMPLETE START_UDP_HOLE_PUNCHING_ADVICE_CANCEL_HAIRPIN jnihelper ] is already registered! ANDROID Windows nsw NATTYPEV6 SEND_COMMAND_DROP_COUNT_BURST_L5 SEND_COMMAND_DROP_COUNT_BURST_L4_MCACTIVE SELF_AUTOMOVE_COUNT_BURST_L2 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L4 RECEIVED_COMMAND_COUNT RECEIVED_VALID_COUNT SENT_VOICE_DATA

OFFSET=0xb43ce9 TERM=TURN
CONTEXT=PEV6 SEND_COMMAND_DROP_COUNT_BURST_L5 SEND_COMMAND_DROP_COUNT_BURST_L4_MCACTIVE SELF_AUTOMOVE_COUNT_BURST_L2 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L4 RECEIVED_COMMAND_COUNT RECEIVED_VALID_COUNT SENT_VOICE_DATA_COUNT_INMATCH AWAY_TEAM_ID_NO TURN_SESSION_RTT_EWMA P2PTURNIO_P2P_RTT_Mean TURN_TCP MAIN_THREAD_ELAPSED_SINCE_LAST_UPDATED VALUE need_root_box_warn_due_to_age CmdSendNotice ticket turn_server_list SendAdjustParamTask 10BASE_HALF WIMAX DisableBroadcasting grpc.http2.write_buffer_size grpc.keepalive_permit_without_calls grpc.xds_locality_retention_interval_ms plugin_credentials grpc_channel_ar

OFFSET=0xb43d02 TERM=TURN
CONTEXT=UNT_BURST_L5 SEND_COMMAND_DROP_COUNT_BURST_L4_MCACTIVE SELF_AUTOMOVE_COUNT_BURST_L2 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L4 RECEIVED_COMMAND_COUNT RECEIVED_VALID_COUNT SENT_VOICE_DATA_COUNT_INMATCH AWAY_TEAM_ID_NO TURN_SESSION_RTT_EWMA P2PTURNIO_P2P_RTT_Mean TURN_TCP MAIN_THREAD_ELAPSED_SINCE_LAST_UPDATED VALUE need_root_box_warn_due_to_age CmdSendNotice ticket turn_server_list SendAdjustParamTask 10BASE_HALF WIMAX DisableBroadcasting grpc.http2.write_buffer_size grpc.keepalive_permit_without_calls grpc.xds_locality_retention_interval_ms plugin_credentials grpc_channel_arguments G:/PES22HC/Dev-60

OFFSET=0xb43d16 TERM=TURN
CONTEXT=MMAND_DROP_COUNT_BURST_L4_MCACTIVE SELF_AUTOMOVE_COUNT_BURST_L2 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L4 RECEIVED_COMMAND_COUNT RECEIVED_VALID_COUNT SENT_VOICE_DATA_COUNT_INMATCH AWAY_TEAM_ID_NO TURN_SESSION_RTT_EWMA P2PTURNIO_P2P_RTT_Mean TURN_TCP MAIN_THREAD_ELAPSED_SINCE_LAST_UPDATED VALUE need_root_box_warn_due_to_age CmdSendNotice ticket turn_server_list SendAdjustParamTask 10BASE_HALF WIMAX DisableBroadcasting grpc.http2.write_buffer_size grpc.keepalive_permit_without_calls grpc.xds_locality_retention_interval_ms plugin_credentials grpc_channel_arguments G:/PES22HC/Dev-600Series/Source/Share

OFFSET=0xb45dfe TERM=TURN
CONTEXT=ATIO_AT_CROSS REVERSE THROWAWAY_DOWN CUT_CUP_LIFT NUM_SEC_PLAY_CUT FLOAT STAGE_HALFWAY NUM_EVERY_N_GAMES SOME_ONE DOWN_STAGGER NUM_GOAL_FROM_PRE STANDARD CONTACT_WALL 04A_TO_CENTER_FROM_SIDE TARGET_IN AMAZING_LONG AMAZING_ANGLE FRIEND EDGE_TURN BLITZ_CROSSING GK_RUSH_OUT TARGET_MAN B1_TEAM0 COMD_STOP CONTACT_END ADX2MEMMAN sys_ger.str sys_use.str sys_nld.str launch NotSet dt530 pc0103 _optional.pak AssetPack TryRedownload RequestDownload:fail [%s] AssetPack TryRedownload RequestDownload:ok [%s] UpdatePath: error:%d [%s] AssetPackManager_requestInfo AssetPack:%s download Cancel! jp/konami/a

OFFSET=0xb52a59 TERM=TURN
CONTEXT=p_2_2_STEP_near_gabriel dash_04_turn_4_4_090_CIRCLE_Oriul dash_06_side_1_4_run_Oriul dash_06_walk_1_4_run_Oriul dash_10_walk_1_4_135_dash_Oriul reaction_contact_0_2_135_act071_02 moveAdjust_05_Slant_FrontBack_3_3_gabriel nearDefense_04_BODYTURN_Slant_2_2_rightback_STEP_near_gabriel autoMove_02_dribble_reverse_stop_leftside_rightside_2_2_STEP_near_gabriel gkclear_f03s03_0_3_045 nearDribble_04_1_dribble_burst_0_4_f135_y0_oriul dm_oop_lineup_f135_idle_0_2_run_045 gkdeflectlate_s02_0_0_y10 dribblerun_arc_3_3m_f067_y0_out_act097 trap_0_3_045_y3_in_act064 trap_0_3_f045_y3_in_act064 dm_miss_sidestep_1_2_

OFFSET=0xb55c17 TERM=TURN
CONTEXT=OnlineSystem\Multiplay\SessionStrategy\OnlineSystemMultiplaySessionStrategyP2pFullMeshWithTurn.cpp ] RP_JSON_DATA SEQ MappingTestIB FilteringTestII Allocate GetNonce |->> [ %s ][ %d ][ %s ] extra E_OK E_STUN_TEST_ERROR E_MUTEX_INVAL FREE_TURN_CHANNEL_BINDING_ABORTED ro.build.version.release XX 8.8.8.8 match_session_not_connected_timeout_sec SERVNAMEV6 PLATFORM_PEERS NUM_GUESTS_END_MATCH MCDEQUEUEHZ_RATE_ MATCH_STOP_COUNT_BUF_EMPTY TURN_QUALITY_DEGRADATION_RATE TURN_SESSION_RESPONSE_WAITING_TIME TURN_SESSION_RTT_MAX TURN_SESSION_ATTRIBUTE_SOFTWARE P2PTURNIO_RX_LOSS_RATE_EVALUATION DCTEST_OPTIMUM_

OFFSET=0xb55cdc TERM=TURN
CONTEXT= E_OK E_STUN_TEST_ERROR E_MUTEX_INVAL FREE_TURN_CHANNEL_BINDING_ABORTED ro.build.version.release XX 8.8.8.8 match_session_not_connected_timeout_sec SERVNAMEV6 PLATFORM_PEERS NUM_GUESTS_END_MATCH MCDEQUEUEHZ_RATE_ MATCH_STOP_COUNT_BUF_EMPTY TURN_QUALITY_DEGRADATION_RATE TURN_SESSION_RESPONSE_WAITING_TIME TURN_SESSION_RTT_MAX TURN_SESSION_ATTRIBUTE_SOFTWARE P2PTURNIO_RX_LOSS_RATE_EVALUATION DCTEST_OPTIMUM_REGION GAME_SERVER_STATS_RECV_ LATENCY_MODE_CONNECT_WAIT_SOCKET LATENCY_MODE_ANNTENA_USER_DATA_SYNC ] 7.16 PlatformSessionManager isAcknowledged nativeOnBuyFinished iab currency nsw_item_id CmdAu

OFFSET=0xb55cfa TERM=TURN
CONTEXT=X_INVAL FREE_TURN_CHANNEL_BINDING_ABORTED ro.build.version.release XX 8.8.8.8 match_session_not_connected_timeout_sec SERVNAMEV6 PLATFORM_PEERS NUM_GUESTS_END_MATCH MCDEQUEUEHZ_RATE_ MATCH_STOP_COUNT_BUF_EMPTY TURN_QUALITY_DEGRADATION_RATE TURN_SESSION_RESPONSE_WAITING_TIME TURN_SESSION_RTT_MAX TURN_SESSION_ATTRIBUTE_SOFTWARE P2PTURNIO_RX_LOSS_RATE_EVALUATION DCTEST_OPTIMUM_REGION GAME_SERVER_STATS_RECV_ LATENCY_MODE_CONNECT_WAIT_SOCKET LATENCY_MODE_ANNTENA_USER_DATA_SYNC ] 7.16 PlatformSessionManager isAcknowledged nativeOnBuyFinished iab currency nsw_item_id CmdAuthSteam address_data_size MOBI

OFFSET=0xb55d1d TERM=TURN
CONTEXT=BORTED ro.build.version.release XX 8.8.8.8 match_session_not_connected_timeout_sec SERVNAMEV6 PLATFORM_PEERS NUM_GUESTS_END_MATCH MCDEQUEUEHZ_RATE_ MATCH_STOP_COUNT_BUF_EMPTY TURN_QUALITY_DEGRADATION_RATE TURN_SESSION_RESPONSE_WAITING_TIME TURN_SESSION_RTT_MAX TURN_SESSION_ATTRIBUTE_SOFTWARE P2PTURNIO_RX_LOSS_RATE_EVALUATION DCTEST_OPTIMUM_REGION GAME_SERVER_STATS_RECV_ LATENCY_MODE_CONNECT_WAIT_SOCKET LATENCY_MODE_ANNTENA_USER_DATA_SYNC ] 7.16 PlatformSessionManager isAcknowledged nativeOnBuyFinished iab currency nsw_item_id CmdAuthSteam address_data_size MOBILE_3G MOBILE_4G MultiStatsUploader 

OFFSET=0xb55d32 TERM=TURN
CONTEXT=on.release XX 8.8.8.8 match_session_not_connected_timeout_sec SERVNAMEV6 PLATFORM_PEERS NUM_GUESTS_END_MATCH MCDEQUEUEHZ_RATE_ MATCH_STOP_COUNT_BUF_EMPTY TURN_QUALITY_DEGRADATION_RATE TURN_SESSION_RESPONSE_WAITING_TIME TURN_SESSION_RTT_MAX TURN_SESSION_ATTRIBUTE_SOFTWARE P2PTURNIO_RX_LOSS_RATE_EVALUATION DCTEST_OPTIMUM_REGION GAME_SERVER_STATS_RECV_ LATENCY_MODE_CONNECT_WAIT_SOCKET LATENCY_MODE_ANNTENA_USER_DATA_SYNC ] 7.16 PlatformSessionManager isAcknowledged nativeOnBuyFinished iab currency nsw_item_id CmdAuthSteam address_data_size MOBILE_3G MOBILE_4G MultiStatsUploader enable_indicator_stat

OFFSET=0xb55d55 TERM=TURN
CONTEXT=_not_connected_timeout_sec SERVNAMEV6 PLATFORM_PEERS NUM_GUESTS_END_MATCH MCDEQUEUEHZ_RATE_ MATCH_STOP_COUNT_BUF_EMPTY TURN_QUALITY_DEGRADATION_RATE TURN_SESSION_RESPONSE_WAITING_TIME TURN_SESSION_RTT_MAX TURN_SESSION_ATTRIBUTE_SOFTWARE P2PTURNIO_RX_LOSS_RATE_EVALUATION DCTEST_OPTIMUM_REGION GAME_SERVER_STATS_RECV_ LATENCY_MODE_CONNECT_WAIT_SOCKET LATENCY_MODE_ANNTENA_USER_DATA_SYNC ] 7.16 PlatformSessionManager isAcknowledged nativeOnBuyFinished iab currency nsw_item_id CmdAuthSteam address_data_size MOBILE_3G MOBILE_4G MultiStatsUploader enable_indicator_stats tue wed GetGPUModelName grpc.seco

OFFSET=0xb659a8 TERM=TURN
CONTEXT=e_stop_rightfront_leftback_3_3_near_gabriel autoMove_04_crank45_loop_3_3_STEP_near_gabriel autoMove_05_zigzag135_front_loop_2_2_STEP_near_gabriel new_dribble_0_4_135_in new_dribble_0_4_180_in lose_overtaken_idle_0_2_f180_act079 autoMove_35_TURNCANCEL_Side_3_3_f090_090_180_STEP_near_gabriel dash_08_dash_4_0_135_neardelay_Oriul autoMove_02_dribble_reverse_stop_leftfront_rightback_1_1_STEP_near_gabriel autoMove_02_dribble_reverse_stop_rightfront_leftback_3_3_STEP_near_gabriel reaction_contact_2_3_180_act079_01 gkdeflectlate_s04_0_0_y00 trap_0_3_090_y3_in_act064 dml_goal_celebrate_0111 js_parallel_int

OFFSET=0xb67c5e TERM=TURN
CONTEXT=_MOVE FEINT_KIND_KICK_OUT_SHOOT FEINT_KIND_HEELLIFT FEINT_KIND_KICKFEINT_VANPERSIE_L FEINT_KIND_INOUT_R FEINT_KIND_SLIDERABONA_L FEINT_KIND_VALDIVIA_KICKFEINT_R FEINT_KIND_DOUBLETOUCH_SCISSORS_R FEINT_KIND_BODYFAKE_COMBO_L FEINT_KIND_SPRINGTURN_L PANEL ML CUP COMMON_L1 MEMBER_CHANGE_PRE_LIMIT PREV_MATCH PREV_PKMATCH ONEMATCH PAST_MIDDLE_NOW PATH_TO_GLORY_RESTART_KIND_PENALTY_KICK SUGOROKU_OBJECT_KIND_DUMMY_BRIDGE_X5 Retry_SetPlayerActionAndParam_action_%d_%d TEAMAI_H cpk_dat/common/match/path_to_glory_replay/path_to_glory_replay_02.rep cpk_dat/common/match/path_to_glory_replay/path_to_glory_replay

OFFSET=0xb6912b TERM=TURN
CONTEXT= CMD_DEMOCHAT platform_id is_finish_select CMD_USER_DATA_SYNC CHANGED_ADDRESS UHP_KEEPALIVE hostAddress STATUS RESTRAINED E_ADD_PORT_MAPPING_IN_BINDING_USE UPNP_RETREIVE_DEVICE_DESCRIPTION_COMPLETE UPNP_QUERY_DEVICE_STATUS_COMPLETE REFRESH_TURN_PERMISSION_BINDING_COMPLETE default_timeout Xb1 IPADDR TX_PPS_ SEND_COMMAND_DROP_COUNT_BURST_L3_MCACTIVE SELF_AUTOMOVE_COUNT_BURST_L4_MCACTIVE EXECUTED_COMMAND_COUNT_MCACTIVE SEND_COMMAND_DROP_COUNT SENT_VOICE_DATA_COUNT MY_SIDE AWAY_TEAM_ID_ID TURN_QUALITY_DEGRADATIONSESSION_RTT_COUNT TURN_SESSION_RTT_MIN LATENCY_TURN_CONNECT_UDP_MIN LATENCY_TURN_CONNECT_P

OFFSET=0xb69225 TERM=TURN
CONTEXT=SSION_BINDING_COMPLETE default_timeout Xb1 IPADDR TX_PPS_ SEND_COMMAND_DROP_COUNT_BURST_L3_MCACTIVE SELF_AUTOMOVE_COUNT_BURST_L4_MCACTIVE EXECUTED_COMMAND_COUNT_MCACTIVE SEND_COMMAND_DROP_COUNT SENT_VOICE_DATA_COUNT MY_SIDE AWAY_TEAM_ID_ID TURN_QUALITY_DEGRADATIONSESSION_RTT_COUNT TURN_SESSION_RTT_MIN LATENCY_TURN_CONNECT_UDP_MIN LATENCY_TURN_CONNECT_PEER_MIN IPV6 IPV_UNKNOWN PROCESSNUM CMD_RETRY_REC LATENCY_MODE_CONNECT_CONNECT_SESSION SURVEY_ANSWER_1 RX_LOSS_RATE_R_MIN %.2f _RES_ info_ CmdRestoreItem getIntroductoryPricePeriod (Lcom/android/billingclient/api/PurchaseHistoryRecord;)Ljava/lang/Str

OFFSET=0xb6924f TERM=TURN
CONTEXT= IPADDR TX_PPS_ SEND_COMMAND_DROP_COUNT_BURST_L3_MCACTIVE SELF_AUTOMOVE_COUNT_BURST_L4_MCACTIVE EXECUTED_COMMAND_COUNT_MCACTIVE SEND_COMMAND_DROP_COUNT SENT_VOICE_DATA_COUNT MY_SIDE AWAY_TEAM_ID_ID TURN_QUALITY_DEGRADATIONSESSION_RTT_COUNT TURN_SESSION_RTT_MIN LATENCY_TURN_CONNECT_UDP_MIN LATENCY_TURN_CONNECT_PEER_MIN IPV6 IPV_UNKNOWN PROCESSNUM CMD_RETRY_REC LATENCY_MODE_CONNECT_CONNECT_SESSION SURVEY_ANSWER_1 RX_LOSS_RATE_R_MIN %.2f _RES_ info_ CmdRestoreItem getIntroductoryPricePeriod (Lcom/android/billingclient/api/PurchaseHistoryRecord;)Ljava/lang/String; (Lcom/android/billingclient/api/Billi

OFFSET=0xb6926c TERM=TURN
CONTEXT=DROP_COUNT_BURST_L3_MCACTIVE SELF_AUTOMOVE_COUNT_BURST_L4_MCACTIVE EXECUTED_COMMAND_COUNT_MCACTIVE SEND_COMMAND_DROP_COUNT SENT_VOICE_DATA_COUNT MY_SIDE AWAY_TEAM_ID_ID TURN_QUALITY_DEGRADATIONSESSION_RTT_COUNT TURN_SESSION_RTT_MIN LATENCY_TURN_CONNECT_UDP_MIN LATENCY_TURN_CONNECT_PEER_MIN IPV6 IPV_UNKNOWN PROCESSNUM CMD_RETRY_REC LATENCY_MODE_CONNECT_CONNECT_SESSION SURVEY_ANSWER_1 RX_LOSS_RATE_R_MIN %.2f _RES_ info_ CmdRestoreItem getIntroductoryPricePeriod (Lcom/android/billingclient/api/PurchaseHistoryRecord;)Ljava/lang/String; (Lcom/android/billingclient/api/BillingResult;Lcom/android/billing

OFFSET=0xb69289 TERM=TURN
CONTEXT=SELF_AUTOMOVE_COUNT_BURST_L4_MCACTIVE EXECUTED_COMMAND_COUNT_MCACTIVE SEND_COMMAND_DROP_COUNT SENT_VOICE_DATA_COUNT MY_SIDE AWAY_TEAM_ID_ID TURN_QUALITY_DEGRADATIONSESSION_RTT_COUNT TURN_SESSION_RTT_MIN LATENCY_TURN_CONNECT_UDP_MIN LATENCY_TURN_CONNECT_PEER_MIN IPV6 IPV_UNKNOWN PROCESSNUM CMD_RETRY_REC LATENCY_MODE_CONNECT_CONNECT_SESSION SURVEY_ANSWER_1 RX_LOSS_RATE_R_MIN %.2f _RES_ info_ CmdRestoreItem getIntroductoryPricePeriod (Lcom/android/billingclient/api/PurchaseHistoryRecord;)Ljava/lang/String; (Lcom/android/billingclient/api/BillingResult;Lcom/android/billingclient/api/BillingConfig;)V a

OFFSET=0xb78ac7 TERM=TURN
CONTEXT=_loop_3_3_mid_gabriel Slower_0_3_090 autoMove_02_reverse_stop_leftside_rightside_3_3_STEP_near_gabriel autoMove_06_zigzag135_side_loop_3_3_near_gabriel dash_08_dash_4_0_090_neardelay_Oriul dash_10_walk_1_4_045_dash_Oriul nearDefense_04_BODYTURN_Slant_3_3_frontback_STEP_near_gabriel nearDefense_04_BODYTURN_Slant_3_3_rightback_STEP_near_gabriel gkcatchslideback_f01_3_0_y04_135 tacklefoot_parallel_near_3_0_f022_act095 feint_drawclose_0_3_000_y0_sole_in_act097 dm_oop_pointing_f090_parallel_2_1_side_000 dm_oop_pointing_f135_parallel_2_2_parallel_000 gkFumble_f00_0_0_y06 dml_goal_celebrate_0087 kick_lon

OFFSET=0xb78b05 TERM=TURN
CONTEXT=leftside_rightside_3_3_STEP_near_gabriel autoMove_06_zigzag135_side_loop_3_3_near_gabriel dash_08_dash_4_0_090_neardelay_Oriul dash_10_walk_1_4_045_dash_Oriul nearDefense_04_BODYTURN_Slant_3_3_frontback_STEP_near_gabriel nearDefense_04_BODYTURN_Slant_3_3_rightback_STEP_near_gabriel gkcatchslideback_f01_3_0_y04_135 tacklefoot_parallel_near_3_0_f022_act095 feint_drawclose_0_3_000_y0_sole_in_act097 dm_oop_pointing_f090_parallel_2_1_side_000 dm_oop_pointing_f135_parallel_2_2_parallel_000 gkFumble_f00_0_0_y06 dml_goal_celebrate_0087 kick_long_3_0_instep_y0_090_pirlo StabilizerCam_idle_0_1_walkside_R St

OFFSET=0xb7939e TERM=TURN
CONTEXT=rtifying_f045 dm_oop_angry_1_3_090_act064_01 LongVersion_201123_F025_t01_act068_03 enum_dummy371 LongVersion_201124_F033_t01_act071_01 enum_dummy392 enum_dummy453 autoMove_04_01_gkmovemid_Sidestep_Angle5_1_1 NEARKEEPER_06_02_gkmovenear_0_3_TURN enum_dummy505 enum_dummy521 enum_dummy550 enum_dummy577 ShortVersion_201123_F001_t01_act071_01 ShortVersion_201123_F003_t01_act068_01 enum_dummy585 enum_dummy586 enum_dummy590 enum_dummy639 defenseMove_01_parallel_3_2_act068 passGetMove_01_run_3_3_f225_act001 gkrise_faceupStepfoot_0_3_000 gkrise_sidewaysup_l_0_0_f090 LongVersion_180929_F051_t03_Gabriel_01 e

OFFSET=0xb7c218 TERM=TURN
CONTEXT=:%08x} pds E_AFNOSUPPORT {"upnp":[ 255.255.255.255 BAD_STATUS_CODE enable_gateway_timeout is_enable_for_match RX_RLOSS_RATE_MEAN_NPI MATCH_STOP_MAX_ROLLING_COUNT_BUF_EMPTY_IV1_MCACTIVE SEND_COMMAND_MUST_NOT_DROP_COUNT_SEND HOME_TEAM_ID_NO TURN_SESSION_RTT_VARIANCE P2PTURNIO_TURN_RX_LOSS_RATE LATENCY_TURN_RESOLVING_NAME_ANY_MEAN CMD_FAILED_COUNT_HTTP CMD_FAILED_COUNT_GRPC PLATFORM IDELAY_MEAN_MCACTIVE it->first: scheme getOfferId (Lcom/android/billingclient/api/Purchase;)Ljava/lang/String; nativeOnGetInventoryFinished android_id obfuscated_account_id need_refund_reversed_detect_notice bonus_coin C

OFFSET=0xb7c235 TERM=TURN
CONTEXT=pnp":[ 255.255.255.255 BAD_STATUS_CODE enable_gateway_timeout is_enable_for_match RX_RLOSS_RATE_MEAN_NPI MATCH_STOP_MAX_ROLLING_COUNT_BUF_EMPTY_IV1_MCACTIVE SEND_COMMAND_MUST_NOT_DROP_COUNT_SEND HOME_TEAM_ID_NO TURN_SESSION_RTT_VARIANCE P2PTURNIO_TURN_RX_LOSS_RATE LATENCY_TURN_RESOLVING_NAME_ANY_MEAN CMD_FAILED_COUNT_HTTP CMD_FAILED_COUNT_GRPC PLATFORM IDELAY_MEAN_MCACTIVE it->first: scheme getOfferId (Lcom/android/billingclient/api/Purchase;)Ljava/lang/String; nativeOnGetInventoryFinished android_id obfuscated_account_id need_refund_reversed_detect_notice bonus_coin CmdSendSessionId.php use_http_

OFFSET=0xb7c23c TERM=TURN
CONTEXT=255.255.255.255 BAD_STATUS_CODE enable_gateway_timeout is_enable_for_match RX_RLOSS_RATE_MEAN_NPI MATCH_STOP_MAX_ROLLING_COUNT_BUF_EMPTY_IV1_MCACTIVE SEND_COMMAND_MUST_NOT_DROP_COUNT_SEND HOME_TEAM_ID_NO TURN_SESSION_RTT_VARIANCE P2PTURNIO_TURN_RX_LOSS_RATE LATENCY_TURN_RESOLVING_NAME_ANY_MEAN CMD_FAILED_COUNT_HTTP CMD_FAILED_COUNT_GRPC PLATFORM IDELAY_MEAN_MCACTIVE it->first: scheme getOfferId (Lcom/android/billingclient/api/Purchase;)Ljava/lang/String; nativeOnGetInventoryFinished android_id obfuscated_account_id need_refund_reversed_detect_notice bonus_coin CmdSendSessionId.php use_http_command

OFFSET=0xb7c256 TERM=TURN
CONTEXT=_CODE enable_gateway_timeout is_enable_for_match RX_RLOSS_RATE_MEAN_NPI MATCH_STOP_MAX_ROLLING_COUNT_BUF_EMPTY_IV1_MCACTIVE SEND_COMMAND_MUST_NOT_DROP_COUNT_SEND HOME_TEAM_ID_NO TURN_SESSION_RTT_VARIANCE P2PTURNIO_TURN_RX_LOSS_RATE LATENCY_TURN_RESOLVING_NAME_ANY_MEAN CMD_FAILED_COUNT_HTTP CMD_FAILED_COUNT_GRPC PLATFORM IDELAY_MEAN_MCACTIVE it->first: scheme getOfferId (Lcom/android/billingclient/api/Purchase;)Ljava/lang/String; nativeOnGetInventoryFinished android_id obfuscated_account_id need_refund_reversed_detect_notice bonus_coin CmdSendSessionId.php use_http_command enable_indicator_stats_fo

OFFSET=0xb8c1f8 TERM=TURN
CONTEXT=_3_000_push_aside_act080_01 avoidslide_0_3_000_push_aside_act084_01 autoMove_02_reverse_stop_front_back_1_1_STEP_near_gabriel autoMove_00_bodyangle_00_90_00_3_3_near_gabriel avoidslide_2_4_000_rapid_low_push_aside_act068_01 autoMove_33_IDLETURN_Slant_45_90_135_180_near_gabriel dash_06_backslnat_1_4_run_Oriul ballTouch_05_5_dribble_touch_mid_3_3_000_y0_gabriel autoMove_01_dribble_reverse_loop_slant_backslant_1_1_STEP_near_gabriel autoMove_02_dribble_reverse_stop_leftfront_rightback_3_3_STEP_near_gabriel gkmovemid_CatchMove_3_3_ball gkmovemid_CatchMove_4_4_ball_v02 nearDribble_04_1_dribble_burst_0_4

OFFSET=0xb8cc3c TERM=TURN
CONTEXT=_dummy419 enum_dummy452 autoMove_00_gkmovemid_step_ChageAngle01_1_1 autoMove_00_gkmovenear_step_ChageAngle01_3_3 autoMove_03_01_gkmovenear_Sidestep_Angle5_3_3 autoMove_04_01_gkmovenear_Sidestep_Angle5_3_3 NEARKEEPER_04_03_gkmovemid_3_3_BODYTURN_SLANT enum_dummy537 gkgoalkick_instruction01_0_0 enum_dummy654 gkrise_sidewaysdownlate_l_0_0_000 gksavingCancel_toSideRun_s03 cpk_dat/common/anime/FoxAnim/Face/CharacterAssets/face_anim_skel.ask cpk_dat/common/anime/FoxAnim/Face/CharacterAssets/face_render_skel.ask base_d_end_cup_hoe base_d_itai_karui base_d_kantoku_siji ef23_shout_loudly neut_breth_eyhc_lo

OFFSET=0xb8f6d0 TERM=TURN
CONTEXT=ETERMN_TIME_MAX MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L2 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L1_MCACTIVE NTL_PEER_KEEPALIVE_COUNT RTO_ SENT_COMMAND_COUNT RECEIVED_VALID_LENGTH PID_PEER HOME_TEAM_ID_ID AT_DEFENCE_BACKGROUND_COUNTS LATENCY_TURN_CONNECT_ANY_MEAN LATENCY_TURN_CONNECT_ANY_VARIANCE TURN_WS SEND_TO_NET_INFO_MAX_NO_SEND_INTERVAL APP_VERSION MANUFACTURERE MIDDLE HIGH QUALITY_SETTING_FOR_PLAYER DOWNLOAD_SERVER_STATS_ LATENCY_MODE_MATCH_SETTEING_INIT LATENCY_MODE_MATCHING_CMD_START_MATCHING SURVEY_ANSWER_2 https://info.service.konami.net/XWW020-E1/info/ ChangeServer.bin getBillingPeriod ge

OFFSET=0xb8f6ee TERM=TURN
CONTEXT=NT_SELF_BUF_EMPTY_BURST_L2 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L1_MCACTIVE NTL_PEER_KEEPALIVE_COUNT RTO_ SENT_COMMAND_COUNT RECEIVED_VALID_LENGTH PID_PEER HOME_TEAM_ID_ID AT_DEFENCE_BACKGROUND_COUNTS LATENCY_TURN_CONNECT_ANY_MEAN LATENCY_TURN_CONNECT_ANY_VARIANCE TURN_WS SEND_TO_NET_INFO_MAX_NO_SEND_INTERVAL APP_VERSION MANUFACTURERE MIDDLE HIGH QUALITY_SETTING_FOR_PLAYER DOWNLOAD_SERVER_STATS_ LATENCY_MODE_MATCH_SETTEING_INIT LATENCY_MODE_MATCHING_CMD_START_MATCHING SURVEY_ANSWER_2 https://info.service.konami.net/XWW020-E1/info/ ChangeServer.bin getBillingPeriod getPurchaseToken getDeveloperPay

OFFSET=0xb8f708 TERM=TURN
CONTEXT= MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L1_MCACTIVE NTL_PEER_KEEPALIVE_COUNT RTO_ SENT_COMMAND_COUNT RECEIVED_VALID_LENGTH PID_PEER HOME_TEAM_ID_ID AT_DEFENCE_BACKGROUND_COUNTS LATENCY_TURN_CONNECT_ANY_MEAN LATENCY_TURN_CONNECT_ANY_VARIANCE TURN_WS SEND_TO_NET_INFO_MAX_NO_SEND_INTERVAL APP_VERSION MANUFACTURERE MIDDLE HIGH QUALITY_SETTING_FOR_PLAYER DOWNLOAD_SERVER_STATS_ LATENCY_MODE_MATCH_SETTEING_INIT LATENCY_MODE_MATCHING_CMD_START_MATCHING SURVEY_ANSWER_2 https://info.service.konami.net/XWW020-E1/info/ ChangeServer.bin getBillingPeriod getPurchaseToken getDeveloperPayload ios_product_id psn_pr

OFFSET=0xba30b7 TERM=TURN
CONTEXT=PLETE ,%s JNIHVoidMethodV ntl_ethernet_portselectpolicy gdk OSVERSION_PEERS SELF_AUTOMOVE_COUNT_BURST_L5 SELF_AUTOMOVE_COUNT_BURST_L1_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L1 RECEIVE_UNKNOWN_ERROR_COUNT MEMORY_VIRTUAL_AVAILABLE_KiB_ P2PTURNIO_TURN_RTT_MEAN P2PTURNIO_RTT_MIN_EVALUATION time, ping_mean, ping_variance, ping_min, ping_max, pes_hz_mean, pes_hz_variance, pes_hz_min, pes_hz_max, ue_hz_mean, ue_hz_variance, ue_hz_min, ue_hz_max, CURRENT_DIVISION LOW LATENCY_MODE_ANNTENA_POLLING_CMD_GET_GAME_SESSION_CHECK_RES LATENCY_MODE_PRE_MENU_READY_ALL_PLAYER MEMPEAK_TEXTURE_STREAM_POOL_SIZE %d_

OFFSET=0xba30be TERM=TURN
CONTEXT=%s JNIHVoidMethodV ntl_ethernet_portselectpolicy gdk OSVERSION_PEERS SELF_AUTOMOVE_COUNT_BURST_L5 SELF_AUTOMOVE_COUNT_BURST_L1_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L1 RECEIVE_UNKNOWN_ERROR_COUNT MEMORY_VIRTUAL_AVAILABLE_KiB_ P2PTURNIO_TURN_RTT_MEAN P2PTURNIO_RTT_MIN_EVALUATION time, ping_mean, ping_variance, ping_min, ping_max, pes_hz_mean, pes_hz_variance, pes_hz_min, pes_hz_max, ue_hz_mean, ue_hz_variance, ue_hz_min, ue_hz_max, CURRENT_DIVISION LOW LATENCY_MODE_ANNTENA_POLLING_CMD_GET_GAME_SESSION_CHECK_RES LATENCY_MODE_PRE_MENU_READY_ALL_PLAYER MEMPEAK_TEXTURE_STREAM_POOL_SIZE %d_%d RX_R

OFFSET=0xba30cf TERM=TURN
CONTEXT=V ntl_ethernet_portselectpolicy gdk OSVERSION_PEERS SELF_AUTOMOVE_COUNT_BURST_L5 SELF_AUTOMOVE_COUNT_BURST_L1_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L1 RECEIVE_UNKNOWN_ERROR_COUNT MEMORY_VIRTUAL_AVAILABLE_KiB_ P2PTURNIO_TURN_RTT_MEAN P2PTURNIO_RTT_MIN_EVALUATION time, ping_mean, ping_variance, ping_min, ping_max, pes_hz_mean, pes_hz_variance, pes_hz_min, pes_hz_max, ue_hz_mean, ue_hz_variance, ue_hz_min, ue_hz_max, CURRENT_DIVISION LOW LATENCY_MODE_ANNTENA_POLLING_CMD_GET_GAME_SESSION_CHECK_RES LATENCY_MODE_PRE_MENU_READY_ALL_PLAYER MEMPEAK_TEXTURE_STREAM_POOL_SIZE %d_%d RX_RLOSS_RATE_R_MIN a

OFFSET=0xbaaa51 TERM=TURN
CONTEXT=tUniformConfigEditName shortPosV wet reflesh_model BlendFacialEyebrowR BlendFacialCheekR BlendEyeblinkL m_skinThighTex padPort GetDebugChoiceUniqueStr GetIcon highPriority ECmnIconNominationType::TYPE_NUM ECommonWidgetLabelKind::FRAME_IN_RETURN_END ETeamSideType AudiAreaPlane ECustomStadiumColorType::GoalnetColor2 ECustomStadiumParamType::GoalnetPattern OnApplyParameter SubsystemHelper EDataStoreValueType::Enum SubComponent EDemoPropInfoFlag::Logo3White SetAwayCharacterRole isDropPointWidgetCenter EDnDTwState::TOUCH_ENTER EDnDTwState::DRAG_CANCEL IsControlable DnDTwDrop SorceWidget DnDTwMouseLeave

OFFSET=0xbb55fc TERM=TURN
CONTEXT=RESULT_SITUATION_FAILED THROUGH GK_JUMPSAVE ANIME_SEAMLESS_CARRY_BALL ANIME_SEAMLESS_CORNERKICK_LONGPASS ANIME_KP_GOALKICK_KICKER_LOOP ANIME_KP_PRE_JUMP ANIME_MAX FEINT_KIND_OUTIN FEINT_KIND_ELASTICO_R FEINT_KIND_TAPFAKE_L FEINT_KIND_SPRINGTURN_R BACKNET ENTRY_CHECK_END FOUL FREE_KICK_KIND UNIQUE_MOTION_BEGIN KICK_OFF CORNER_KICK MATCH_LEVEL_TOPPLAYER PATH_TO_GLORY_RESTART_KIND_CORNER_KICK PATH_TO_GLORY_CONE_KIND_DASH TUTORIAL_OBJECT_KIND_DUMMY_BRIDGE_X4 match::ReplayCameraListener InputTextAlert MenuEvCompeCompeEventCompeCampaignRanking Online/Lobby/MenuLobbyDivideCoopTeam LobbyMainSelect /Game/A

OFFSET=0xbb6aff TERM=TURN
CONTEXT=AVAIL UPNP_DELETE_PORT_FORWARDING_COMPLETE JP CheckLinkDownThread is_enable Def_Online_Use_Cronet nn_network_request_on_resume NUM_GUESTS_BEGIN_MATCH NETWORK_DOWN_COUNT IP_ADDRESS_HOP_2_ICMP_END_TEST OFFICIAL_COMPETITION_TYPE IS_EX LATENCY_TURN_CONNECT_PEER_MAX DOWNLOAD_SERVER_STATS_RECV_URL IPV4ONLY_ARPA V4_UDP_SOCKET_ERROR 0x%08x bl_details_switching CmdSetKgsPurchaseUnlocked getType isSubscriptionsSupported (Lcom/android/billingclient/api/Purchase;)V CmdRestoreItem.php CmdGetSessionId.php CmdConnectGrpc.php M4 jp/konami/android/common/BroadcastPermitter isDeviceRooted jp/konami/android/common/S

OFFSET=0xbc714e TERM=TURN
CONTEXT=_act064_01 enum_dummy344 enum_dummy348 LongVersion_201124_F032_t01_act068_02 enum_dummy375 enum_dummy382 enum_dummy409 enum_dummy412 enum_dummy432 autoMove_00_01_gkmovenear_FrontBackLoop_slant_Angle5_2_2 NEARKEEPER_04_03_gkmovenear_2_2_BODYTURN_SLANT enum_dummy464 enum_dummy516 enum_dummy534 enum_dummy535 ShortVersion_201123_F002_t01_act068_03 enum_dummy588 enum_dummy600 block_0_0_y01_090_act071 block_neardelayside_2_0_y00_000_far_act068 enum_dummy656 defenseMove_01_parallel_3_3_act068 passGetMove_01_run_3_3_f270_act071 demo%03d isRandomFace base_goal_hoe head_brwup_unnos_eyhc loss_brwtrb_mmov_sof

OFFSET=0xbca089 TERM=TURN
CONTEXT=/PES22HC/Dev-600Series/Source/Shared/basic/ext/grpc/grpc/include/grpcpp/impl/codegen/server_interceptor.h G:/PES22HC/Dev-600Series/Source/Shared/basic/ext/grpc/grpc/include/grpcpp/impl/codegen/proto_buffer_reader.h queue.num_items() == 0 RETURN_EVENT[%p]: %s stream_id @precise: tcp->read_cb == nullptr BACKUP_POLLER:%p uncover cnt %d->%d recvmsg TCP:%p do_read Unknown trace var: '%s' G:\PES22HC\Dev-600Series\Source\Shared\basic\ext\grpc\grpc\src\core\lib\iomgr\ev_poll_posix.cc old > n User called a notify_on function with a previous callback still pending check for SO_REUSEPORT mutator size <= (soc

OFFSET=0xbd99f4 TERM=TURN
CONTEXT=t068_01 avoidjumpsliding_3_4_045_act068_02 avoidslide_1_4_000_rapid_low_push_aside_act068_01 autoMove_02_reverse_stop_rightfront_leftback_2_2_STEP_near_gabriel autoMove_00_dribble_bodyangle_00_90_00_1_1_STEP_near_gabriel nearDefense_04_BODYTURN_Slant_1_1_rightback_STEP_near_gabriel nearDefense_04_BODYTURN_Slant_2_2_f45_f90_f135_reverse_near_gabriel nearDribble_04_1_dribble_burst_2_4_045_y0_oriul dm_miss_idle_0_1_walk_repent_slap_knee_090 gkEmagencyMove_backrun_heisouback_3_4 dml_goal_celebrate_0104 gksavingCancel_toSidelight_s03 dm_oop_pass_point_f090_run_3_3_f090 dm_oop_pointing_f090_mid_delaysid

OFFSET=0xbd9a32 TERM=TURN
CONTEXT=rapid_low_push_aside_act068_01 autoMove_02_reverse_stop_rightfront_leftback_2_2_STEP_near_gabriel autoMove_00_dribble_bodyangle_00_90_00_1_1_STEP_near_gabriel nearDefense_04_BODYTURN_Slant_1_1_rightback_STEP_near_gabriel nearDefense_04_BODYTURN_Slant_2_2_f45_f90_f135_reverse_near_gabriel nearDribble_04_1_dribble_burst_2_4_045_y0_oriul dm_miss_idle_0_1_walk_repent_slap_knee_090 gkEmagencyMove_backrun_heisouback_3_4 dml_goal_celebrate_0104 gksavingCancel_toSidelight_s03 dm_oop_pass_point_f090_run_3_3_f090 dm_oop_pointing_f090_mid_delayside_1_1_R dm_oop_pointing_f090_mid_delayside_2_2_R dm_oop_pointi

OFFSET=0xbda1e4 TERM=TURN
CONTEXT=dummy381 enum_dummy422 enum_dummy433 autoMove_05_01_gkmovemid_Sidestep_Angle5_1_1 autoMove_08_02_gkmovemid_Sidestep_Angle5_1_1 autoMove_33_01_gkmovemid_idle_idleturn_0_0 NEARKEEPER_03_01_gkmovenear_0_3_0 NEARKEEPER_04_02_gkmovenear_3_3_BODYTURN_SLANT enum_dummy475 enum_dummy487 enum_dummy513 enum_dummy523 enum_dummy532 enum_dummy556 enum_dummy578 enum_dummy608 block_neardelayside_2_0_y02_000_near_act071 defenseMove_01_neardelayback_3_3_parallel_f045_act071 gkrise_sidewaysuplate_l_0_0_f090 REFEREEC angr_brwnit_bite_soft base_d_end_banzai_warai base_d_kantoku_warai base_shoot_hit base_syucyu_nirami 

OFFSET=0xbdc991 TERM=TURN
CONTEXT=on ## Stun Profile ${"ip":"%s","rap":%d,"nr":%d,"avg":%d,"max":%d,"min":%d} ## EventHistory E_NETUNREACH E_NO_DELEGATE TARGET_STUN_SERVER jp/konami/android/common/IabBroadcastReceiver NODE_ID_PEER RECEIVED_LENGTH MATCH_SETTING_TIMEZONE TURN_QUALITY_DEGRADATION_RTT_COUNT LATENCY_TURN_RESOLVING_NAME_MAX GAME_SERVER_STATS_SEND_URL LATENCY_MODE_ANNTENA APP_YIELD_STATS_ACTIVITY_TIME_MS TRANSPORT_RTT_MEAN receipt_check_retry_count CmdVerifyUserCanBuy CmdSaveReceipt getIconUrl getPriceAmountMicros getRecurrenceMode getItemProductDetails com/android/billingclient/api/Purchase need_refund_detect_notice

OFFSET=0xbdc9bc TERM=TURN
CONTEXT=r":%d,"avg":%d,"max":%d,"min":%d} ## EventHistory E_NETUNREACH E_NO_DELEGATE TARGET_STUN_SERVER jp/konami/android/common/IabBroadcastReceiver NODE_ID_PEER RECEIVED_LENGTH MATCH_SETTING_TIMEZONE TURN_QUALITY_DEGRADATION_RTT_COUNT LATENCY_TURN_RESOLVING_NAME_MAX GAME_SERVER_STATS_SEND_URL LATENCY_MODE_ANNTENA APP_YIELD_STATS_ACTIVITY_TIME_MS TRANSPORT_RTT_MEAN receipt_check_retry_count CmdVerifyUserCanBuy CmdSaveReceipt getIconUrl getPriceAmountMicros getRecurrenceMode getItemProductDetails com/android/billingclient/api/Purchase need_refund_detect_notice CmdSaveReceipt.php CmdAuthSteam.php turn_a

OFFSET=0xbec138 TERM=TURN
CONTEXT=_front_loop_2_2_STEP_mid_michael dml_goal_celebrate_0335 head_y09_jostle_s_0_0_090_act064 avoidjumpsliding_3_3_f045_act079_01 avoidslide_1_4_090_push_aside_act068_02 autoMove_00_dribble_bodyangle_00_180_00_2_2_STEP_near_gabriel autoMove_35_TURNCANCEL_Back_3_3_f090_090_180_STEP_near_gabriel dash_09_idle_0_4_045_dash_Oriul nearDefense_04_BODYTURN_Slant_2_2_frontback_reverse_STEP_near_gabriel nearDribble_04_1_dribble_burst_0_4_f180_y0_oriul gkEmagencyMove_front_0_4 feintrun_drawclose_3_3_045_y0_sole_in_act097 dm_oop_waitpose_045_walkback_1_2_run_f135 dml_goal_celebrate_0235 gkoverthrow_3_0_fast_000 t

OFFSET=0xbec19e TERM=TURN
CONTEXT=ding_3_3_f045_act079_01 avoidslide_1_4_090_push_aside_act068_02 autoMove_00_dribble_bodyangle_00_180_00_2_2_STEP_near_gabriel autoMove_35_TURNCANCEL_Back_3_3_f090_090_180_STEP_near_gabriel dash_09_idle_0_4_045_dash_Oriul nearDefense_04_BODYTURN_Slant_2_2_frontback_reverse_STEP_near_gabriel nearDribble_04_1_dribble_burst_0_4_f180_y0_oriul gkEmagencyMove_front_0_4 feintrun_drawclose_3_3_045_y0_sole_in_act097 dm_oop_waitpose_045_walkback_1_2_run_f135 dml_goal_celebrate_0235 gkoverthrow_3_0_fast_000 tackleshoulder_0_0_interrupt_blast_000_act102 dml_goal_celebrate_0061 dml_goal_celebrate_0117 dm_oop_po

OFFSET=0xbecab2 TERM=TURN
CONTEXT=ongVersion_201123_F030_t01_act071_01 enum_dummy374 ShortVersion_201123_F017_t01_act068_02 enum_dummy384 enum_dummy441 autoMove_00_gkmovenear_step_ChageAngle02_1_1 autoMove_06_01_gkmovemid_Sidestep_Angle5_2_2 NEARKEEPER_06_01_gkmovenear_1_3_TURN enum_dummy467 enum_dummy488 enum_dummy527 enum_dummy570 enum_dummy596 ShortVersion_201123_F010_t01_act068_04 enum_dummy632 gkgoalkick_instruction03_0_0 block_neardelayside_2_0_y00_000_near_act068 defenseMove_01_parallel_4_0_135_neardelay_act068 gkrise_faceup_0_0_f060 angr_brwnit_lorol base_d_end_photo_talk base_d_kantoku_ikari base_syucyu bitter_brwnit_talk

OFFSET=0xbef5e7 TERM=TURN
CONTEXT=73_CR_XADDR SEND UHP_CONNECT ST UDN NewLeaseDuration ${"%s":%08x} CoreNatTypeUpdate {"titleCode":"%s","locale":"%s","version":"%s","extra":"%s","apiLevel":"%d"} INIT ACCEPTABLE E_NOIMPL E_SOAP_METHOD_NOSUPPORT UPNP_DISCOVERY_COMPLETE ALLOC_TURN_PORT_ALLOCATION_MISSMATCH_ERROR FREE_TURN_PERMISSION_BINDING_ERROR KEEP_UDP_HOLE_PUNCHING_COMPLETE TARGET_TURN_SERVER CallObjectMethod NULL!!: %s {"default": {"onmode": {"get_game_result_error_sec": 30, "game_result_timeout_sec": 45, "at_match_polling_interval_msec": 30000},"timeout": {"CMD_ADD_SCORE": 30, "CMD_ADD_FOUL": 30, "CMD_CHANGE_GAMEPHASE": 30},"in

OFFSET=0xbef611 TERM=TURN
CONTEXT=seDuration ${"%s":%08x} CoreNatTypeUpdate {"titleCode":"%s","locale":"%s","version":"%s","extra":"%s","apiLevel":"%d"} INIT ACCEPTABLE E_NOIMPL E_SOAP_METHOD_NOSUPPORT UPNP_DISCOVERY_COMPLETE ALLOC_TURN_PORT_ALLOCATION_MISSMATCH_ERROR FREE_TURN_PERMISSION_BINDING_ERROR KEEP_UDP_HOLE_PUNCHING_COMPLETE TARGET_TURN_SERVER CallObjectMethod NULL!!: %s {"default": {"onmode": {"get_game_result_error_sec": 30, "game_result_timeout_sec": 45, "at_match_polling_interval_msec": 30000},"timeout": {"CMD_ADD_SCORE": 30, "CMD_ADD_FOUL": 30, "CMD_CHANGE_GAMEPHASE": 30},"invitation_task": {"enable": true, "use_http

OFFSET=0xbef656 TERM=TURN
CONTEXT="%s","version":"%s","extra":"%s","apiLevel":"%d"} INIT ACCEPTABLE E_NOIMPL E_SOAP_METHOD_NOSUPPORT UPNP_DISCOVERY_COMPLETE ALLOC_TURN_PORT_ALLOCATION_MISSMATCH_ERROR FREE_TURN_PERMISSION_BINDING_ERROR KEEP_UDP_HOLE_PUNCHING_COMPLETE TARGET_TURN_SERVER CallObjectMethod NULL!!: %s {"default": {"onmode": {"get_game_result_error_sec": 30, "game_result_timeout_sec": 45, "at_match_polling_interval_msec": 30000},"timeout": {"CMD_ADD_SCORE": 30, "CMD_ADD_FOUL": 30, "CMD_CHANGE_GAMEPHASE": 30},"invitation_task": {"enable": true, "use_http_command": false},"connect_grpc_task": {"disable": true}}} steam PIDS

OFFSET=0xbef891 TERM=TURN
CONTEXT=": {"disable": true}}} steam PIDS _MCACTIVE BEST_ADDRESS_FAMILY CONGESTION_CONTROL_PPS_ SELF_AUTOMOVE_COUNT_BURST_L1 MATCH_CONTROL_SESSION_SEND_HEADER_DELTATIME_MS_ RECEIVED_COUNT RECEIVED_VOICE_DATA_LENGTH IP_ADDRESS_HOP_2_ICMP_BEGIN_TEST TURN_QUALITY_DEGRADATION_RTT_MEAN TURN_QUALITY_DEGRADATIONSESSION_TRANSPORT_RTT_MEAN P2PTURNIO_P2P_RTT_Min LATENCY_TURN_RESOLVING_NAME_MIN 0x%x CS_SERVER_ADDRESS LATENCY_NTL_PUNCHING_PROCESS_ON_SUCCESS LATENCY_MODE_CONNECT LATENCY_MODE_MATCHING_CMD_GET_SERVER_ENV LATENCY_MODE_SESSION_PROCESS_CMD_GET_GAME_SESSION MEMPEAK_GAME_STATE_MISC_BITS V6_TCP_SOCKET_ERROR A

OFFSET=0xbef8b3 TERM=TURN
CONTEXT=_MCACTIVE BEST_ADDRESS_FAMILY CONGESTION_CONTROL_PPS_ SELF_AUTOMOVE_COUNT_BURST_L1 MATCH_CONTROL_SESSION_SEND_HEADER_DELTATIME_MS_ RECEIVED_COUNT RECEIVED_VOICE_DATA_LENGTH IP_ADDRESS_HOP_2_ICMP_BEGIN_TEST TURN_QUALITY_DEGRADATION_RTT_MEAN TURN_QUALITY_DEGRADATIONSESSION_TRANSPORT_RTT_MEAN P2PTURNIO_P2P_RTT_Min LATENCY_TURN_RESOLVING_NAME_MIN 0x%x CS_SERVER_ADDRESS LATENCY_NTL_PUNCHING_PROCESS_ON_SUCCESS LATENCY_MODE_CONNECT LATENCY_MODE_MATCHING_CMD_GET_SERVER_ENV LATENCY_MODE_SESSION_PROCESS_CMD_GET_GAME_SESSION MEMPEAK_GAME_STATE_MISC_BITS V6_TCP_SOCKET_ERROR ACTUAL_MATCH_HZ_MEAN LAST_SERVNAME 

OFFSET=0xbef8e9 TERM=TURN
CONTEXT=SELF_AUTOMOVE_COUNT_BURST_L1 MATCH_CONTROL_SESSION_SEND_HEADER_DELTATIME_MS_ RECEIVED_COUNT RECEIVED_VOICE_DATA_LENGTH IP_ADDRESS_HOP_2_ICMP_BEGIN_TEST TURN_QUALITY_DEGRADATION_RTT_MEAN TURN_QUALITY_DEGRADATIONSESSION_TRANSPORT_RTT_MEAN P2PTURNIO_P2P_RTT_Min LATENCY_TURN_RESOLVING_NAME_MIN 0x%x CS_SERVER_ADDRESS LATENCY_NTL_PUNCHING_PROCESS_ON_SUCCESS LATENCY_MODE_CONNECT LATENCY_MODE_MATCHING_CMD_GET_SERVER_ENV LATENCY_MODE_SESSION_PROCESS_CMD_GET_GAME_SESSION MEMPEAK_GAME_STATE_MISC_BITS V6_TCP_SOCKET_ERROR ACTUAL_MATCH_HZ_MEAN LAST_SERVNAME RX_RLOSS_RATE_R_VARIANCE 

OFFSET=0xbef904 TERM=TURN
CONTEXT=1 MATCH_CONTROL_SESSION_SEND_HEADER_DELTATIME_MS_ RECEIVED_COUNT RECEIVED_VOICE_DATA_LENGTH IP_ADDRESS_HOP_2_ICMP_BEGIN_TEST TURN_QUALITY_DEGRADATION_RTT_MEAN TURN_QUALITY_DEGRADATIONSESSION_TRANSPORT_RTT_MEAN P2PTURNIO_P2P_RTT_Min LATENCY_TURN_RESOLVING_NAME_MIN 0x%x CS_SERVER_ADDRESS LATENCY_NTL_PUNCHING_PROCESS_ON_SUCCESS LATENCY_MODE_CONNECT LATENCY_MODE_MATCHING_CMD_GET_SERVER_ENV LATENCY_MODE_SESSION_PROCESS_CMD_GET_GAME_SESSION MEMPEAK_GAME_STATE_MISC_BITS V6_TCP_SOCKET_ERROR ACTUAL_MATCH_HZ_MEAN LAST_SERVNAME RX_RLOSS_RATE_R_VARIANCE Onlin

OFFSET=0xbff24d TERM=TURN
CONTEXT=03_crank90_loop_3_3_near_gabriel autoMove_00_bodyangle_00_180_00_2_2_STEP_near_gabriel autoMove_01_dribble_reverse_loop_front_back_3_3_STEP_near_gabriel ballTouch_03_3_dribble_player_wrap_around_2_2_045_and_090_y0_take2_gabriel autoMove_35_TURNCANCEL_Front_3_3_f090_090_180_STEP_near_gabriel new_dribble_0_4_f135_sole moveAdjust_05_Slant_FrontBack_2_2_gabriel gkdeflectClear_f03_0_0_y00_090 gkdeflect_f05_3_0_y10_045 reaction_contact_2_3_135_act071_01 nearDribble_04_1_dribble_burst_1_4_090_y0_oriul gkblockcover_f02_0_0_y02_lie tacklefoot_parallel_mid_3_0_000_act095 trap_0_3_f135_y3_in_act064 dm_miss_r

OFFSET=0xbffc61 TERM=TURN
CONTEXT=312 enum_dummy320 enum_dummy333 enum_dummy351 LongVersion_201123_F027_t01_act071_01 ShortVersion_201123_F022_t01_act068_02 enum_dummy460 bench_sit_cross_leg_2 autoMove_03_01_gkmovemid_Sidestep_Angle5_1_1 NEARKEEPER_04_01_gkmovenear_2_2_BODYTURN_SLANT enum_dummy495 enum_dummy519 enum_dummy584 enum_dummy587 enum_dummy610 enum_dummy642 cpk_dat/common/anime/FHSequence/bin/Handrbase.bin base_d_end_banzai_yes ef23_failure_shout ef23_smile_talk loss_brwtrb_mmov_eyc loss_brwtrb_talk_eyhc_soft neut_breath_dribble_S_01 neut_breath_short_head_S_02 neut_watch pose_angry_shout_L_03 pose_angry_shout_M_02 pose_a

OFFSET=0xc026e3 TERM=TURN
CONTEXT=%s xmlns:m="%s"> NewUptime NewPortMappingDescription DeletePortMapping UDP ## NetworkInfo ${"%s":[%d,%d,%d,%d]} ${"%s":0x%08x} ${"%s":"%s"} ${"%s":"%s"} ${"%s":"%s"} ## UpdateWarning ${"Update:":%d} ${"Recv:":%d} E_TIMEOUT E_BADF ALLOC_TURN_PORT_QUOTA_ERROR REFRESH_TURN_PERMISSION_BINDING_ERROR FREE_TURN_PERMISSION_BINDING_COMPLETE ALLOC_TURN_CHANNEL_BINDING_ABORTED STUN_PING_COMPLETE ntl_portcontext_update NODE_ID SEND_COMMAND_DROP_COUNT_BURST_L4 ACTUAL_MATCH_HZ_ ACCESS_LINE_TEST_COUNT IDELAY_BUF_SIZE_CORRECTION_VALUE_ MATCH_SETTING_SEASON TURN_UDP CS_SERVER_LABEL TURN_IO_SET_SESSION_ERROR LA

OFFSET=0xc02701 TERM=TURN
CONTEXT=PortMappingDescription DeletePortMapping UDP ## NetworkInfo ${"%s":[%d,%d,%d,%d]} ${"%s":0x%08x} ${"%s":"%s"} ${"%s":"%s"} ${"%s":"%s"} ## UpdateWarning ${"Update:":%d} ${"Recv:":%d} E_TIMEOUT E_BADF ALLOC_TURN_PORT_QUOTA_ERROR REFRESH_TURN_PERMISSION_BINDING_ERROR FREE_TURN_PERMISSION_BINDING_COMPLETE ALLOC_TURN_CHANNEL_BINDING_ABORTED STUN_PING_COMPLETE ntl_portcontext_update NODE_ID SEND_COMMAND_DROP_COUNT_BURST_L4 ACTUAL_MATCH_HZ_ ACCESS_LINE_TEST_COUNT IDELAY_BUF_SIZE_CORRECTION_VALUE_ MATCH_SETTING_SEASON TURN_UDP CS_SERVER_LABEL TURN_IO_SET_SESSION_ERROR LATENCY_MODE_PRE_MENU_CMD_START_

OFFSET=0xc02724 TERM=TURN
CONTEXT=pping UDP ## NetworkInfo ${"%s":[%d,%d,%d,%d]} ${"%s":0x%08x} ${"%s":"%s"} ${"%s":"%s"} ${"%s":"%s"} ## UpdateWarning ${"Update:":%d} ${"Recv:":%d} E_TIMEOUT E_BADF ALLOC_TURN_PORT_QUOTA_ERROR REFRESH_TURN_PERMISSION_BINDING_ERROR FREE_TURN_PERMISSION_BINDING_COMPLETE ALLOC_TURN_CHANNEL_BINDING_ABORTED STUN_PING_COMPLETE ntl_portcontext_update NODE_ID SEND_COMMAND_DROP_COUNT_BURST_L4 ACTUAL_MATCH_HZ_ ACCESS_LINE_TEST_COUNT IDELAY_BUF_SIZE_CORRECTION_VALUE_ MATCH_SETTING_SEASON TURN_UDP CS_SERVER_LABEL TURN_IO_SET_SESSION_ERROR LATENCY_MODE_PRE_MENU_CMD_START_GAME V4_TCP_SOCKET_ERROR UE_THREAD_

OFFSET=0xc0274b TERM=TURN
CONTEXT=,%d,%d]} ${"%s":0x%08x} ${"%s":"%s"} ${"%s":"%s"} ${"%s":"%s"} ## UpdateWarning ${"Update:":%d} ${"Recv:":%d} E_TIMEOUT E_BADF ALLOC_TURN_PORT_QUOTA_ERROR REFRESH_TURN_PERMISSION_BINDING_ERROR FREE_TURN_PERMISSION_BINDING_COMPLETE ALLOC_TURN_CHANNEL_BINDING_ABORTED STUN_PING_COMPLETE ntl_portcontext_update NODE_ID SEND_COMMAND_DROP_COUNT_BURST_L4 ACTUAL_MATCH_HZ_ ACCESS_LINE_TEST_COUNT IDELAY_BUF_SIZE_CORRECTION_VALUE_ MATCH_SETTING_SEASON TURN_UDP CS_SERVER_LABEL TURN_IO_SET_SESSION_ERROR LATENCY_MODE_PRE_MENU_CMD_START_GAME V4_TCP_SOCKET_ERROR UE_THREAD_LAST_UPDATED BACKGROUND_NOW Def_System_

OFFSET=0xc0281a TERM=TURN
CONTEXT=ERMISSION_BINDING_COMPLETE ALLOC_TURN_CHANNEL_BINDING_ABORTED STUN_PING_COMPLETE ntl_portcontext_update NODE_ID SEND_COMMAND_DROP_COUNT_BURST_L4 ACTUAL_MATCH_HZ_ ACCESS_LINE_TEST_COUNT IDELAY_BUF_SIZE_CORRECTION_VALUE_ MATCH_SETTING_SEASON TURN_UDP CS_SERVER_LABEL TURN_IO_SET_SESSION_ERROR LATENCY_MODE_PRE_MENU_CMD_START_GAME V4_TCP_SOCKET_ERROR UE_THREAD_LAST_UPDATED BACKGROUND_NOW Def_System_PESVERSION_FAKE_ENABLE getSku initializeIAB nativeOnQueryPurchaseHistoryAsyncFinished (Lcom/android/billingclient/api/BillingResult;Ljava/util/List;)V (Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)

OFFSET=0xc02833 TERM=TURN
CONTEXT=E ALLOC_TURN_CHANNEL_BINDING_ABORTED STUN_PING_COMPLETE ntl_portcontext_update NODE_ID SEND_COMMAND_DROP_COUNT_BURST_L4 ACTUAL_MATCH_HZ_ ACCESS_LINE_TEST_COUNT IDELAY_BUF_SIZE_CORRECTION_VALUE_ MATCH_SETTING_SEASON TURN_UDP CS_SERVER_LABEL TURN_IO_SET_SESSION_ERROR LATENCY_MODE_PRE_MENU_CMD_START_GAME V4_TCP_SOCKET_ERROR UE_THREAD_LAST_UPDATED BACKGROUND_NOW Def_System_PESVERSION_FAKE_ENABLE getSku initializeIAB nativeOnQueryPurchaseHistoryAsyncFinished (Lcom/android/billingclient/api/BillingResult;Ljava/util/List;)V (Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)I verified_str_list thu %

OFFSET=0xc07a30 TERM=TURN
CONTEXT= supported size Failed to scan duration written after #EXTINF due to a parse error. != E2018020104:CriHttpRequestAndroid Instance in java layer(jobject) is null. E2021080802:[M2tsSplit] Could not allocate memory for video es (%d [byte]) RETURN criAdo_SetMute(%p, %d). X-TimeSeekRange [CriVodStm] Download EncryptionKey failed. [CriVodStm] An AES-128 encryption key has invalid size. The size is %d. LOCAL: %d:%02d:%02d.%03d%n AndroidThunkJava_LaunchURL (I)Lcom/epicgames/ue4/GameActivity$InputDeviceInfo; AndroidThunkJava_SendBroadcast AndroidThunkJava_HasIntentExtrasKey Unknown LoadPreInitModules C

OFFSET=0xc0a098 TERM=TURN
CONTEXT=InactiveAnimation PlayDecideReleasedAnimation SetCursorLeaveTextInputColor cursorLeaveAnimation DecideReleasedAnimation SetFFameInfo GetRewardTypeCPP ECmnMatchLabelAlignment::LEFT ECmnMatchLabelKind::MAX ECommonWidgetLabelKind::FRAME_OUT_RETURN SeatColor InstancedCrowdInstanceData ECustomStadiumParamType::PitchsideObject1 StringValue AwayTeamIdChanged ControlFlagsChanged GetAwayTeamId GetCaptionNo GetEndDemoWinSide GetViewPlayerPoseKind SetViewCameraNo pWidgetCanvasPanelSlot EDnDTwState::DROP EfbxIsEyeUVScroll UpdateMaterialFaceParam DebugWipeInit RemoveCurrentWidgets StartFadeOut DynamicTextureNr

OFFSET=0xc13158 TERM=TURN
CONTEXT=3_F028_t01_act071_02 LongVersion_201123_F030_t01_act068_01 LongVersion_201123_F030_t02_act071_01 LongVersion_201124_F031_t01_act071_03 enum_dummy380 enum_dummy406 enum_dummy410 enum_dummy443 enum_dummy448 NEARKEEPER_04_01_gkmovemid_2_2_BODYTURN_SLANT NEARKEEPER_06_01_gkmovenear_0_3_TURN enum_dummy470 enum_dummy494 enum_dummy506 enum_dummy528 enum_dummy554 ShortVersion_201123_F002_t01_act071_01 enum_dummy597 enum_dummy622 block_neardelayside_2_0_y00_000_act080 block_neardelayside_2_0_y01_180_far_act071 LongVersion_201123_F030_t03_act068_01 REFEREEB Coach HOME cpk_dat/common/anime/FHSequence/bin/Han

OFFSET=0xc13183 TERM=TURN
CONTEXT=0_t01_act068_01 LongVersion_201123_F030_t02_act071_01 LongVersion_201124_F031_t01_act071_03 enum_dummy380 enum_dummy406 enum_dummy410 enum_dummy443 enum_dummy448 NEARKEEPER_04_01_gkmovemid_2_2_BODYTURN_SLANT NEARKEEPER_06_01_gkmovenear_0_3_TURN enum_dummy470 enum_dummy494 enum_dummy506 enum_dummy528 enum_dummy554 ShortVersion_201123_F002_t01_act071_01 enum_dummy597 enum_dummy622 block_neardelayside_2_0_y00_000_act080 block_neardelayside_2_0_y01_180_far_act071 LongVersion_201123_F030_t03_act068_01 REFEREEB Coach HOME cpk_dat/common/anime/FHSequence/bin/Handlbase.bin base_d_warai_yurui base_g_shoot_

OFFSET=0xc15c11 TERM=TURN
CONTEXT=HOLE_PUNCHING_ERROR KEEPALIVE PEER_HOST pes_thread_onsys_manager total_timeout IOS android ps5 XBX onmode NATTYPE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L3_MCACTIVE MATCH_STOP_MAX_ROLLING_COUNT_BUF_EMPTY_IV3_MCACTIVE AT_OFFENCE_BACKGROUND_COUNTS TURN_CHANGEOVER_TIME P2PTURNIO_RTT_MEAN_EVALUATION PING_ANTENNA_LEVEL END_REASON OPERATION_TYPE CS_SERVER_NAME GAME_SERVER_STATS_URL TRANSPORT_RTT_MAX CmdConsumeItem consumeItem nativeOnGetBillingConfigFinished pes_receipt CmdSendNotice.php wait_msec_cmd_turn_address on_sys_common_thread_pool fri statvfs error grpc.max_connection_age_ms grpc.enable_channelz G:/P

OFFSET=0xc15c29 TERM=TURN
CONTEXT=ALIVE PEER_HOST pes_thread_onsys_manager total_timeout IOS android ps5 XBX onmode NATTYPE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L3_MCACTIVE MATCH_STOP_MAX_ROLLING_COUNT_BUF_EMPTY_IV3_MCACTIVE AT_OFFENCE_BACKGROUND_COUNTS TURN_CHANGEOVER_TIME P2PTURNIO_RTT_MEAN_EVALUATION PING_ANTENNA_LEVEL END_REASON OPERATION_TYPE CS_SERVER_NAME GAME_SERVER_STATS_URL TRANSPORT_RTT_MAX CmdConsumeItem consumeItem nativeOnGetBillingConfigFinished pes_receipt CmdSendNotice.php wait_msec_cmd_turn_address on_sys_common_thread_pool fri statvfs error grpc.max_connection_age_ms grpc.enable_channelz G:/PES22HC/Dev-600Series/Sou

OFFSET=0x9bfa53 TERM=Turn
CONTEXT=erStereoGazeData EMediaVideoCaptureDeviceFilter::Webcam EMediaAudioCaptureDeviceFilter EMediaPlayerTrack GetTrackFormat EMediaSoundChannels::Stereo SetEnableEnvelopeFollowing MTOF_MAX BindingOverrides EHDRCaptureGamut CustomFrameRate bAllowTurning bUsePathTracer G:/UE4.26_eFB/Base/Engine/Source/Runtime/Engine/Classes/AI/AISystemBase.h GeomOverlapBlocking OnComponentSleep G:/UE4.26_eFB/Base/Engine/Source/Runtime/Engine/Private/PhysicsEngine/PhysicsInterfacePhysX.cpp StreamingPool DemoNumActiveObjects ForwardX ActorSpawning PointLights HISMCClusterTree HighResScreenshotMask MorphTargets USoundBase::

OFFSET=0x9c6af1 TERM=Turn
CONTEXT=user_id_data.dat IsSuccessed gzip InputDelayBufferSizeRecentBasicStatisticsMaxSize LatencyWarningLv1ConditionQueueingSizeThreshold MinCorrection CorrectionRiseDeterminationNotReadyForCommandDeltaCountThresholdLow EnableManufactureModelName TurnBufferCriticalConditionTimeCoef TurnNetworkIoReconnectServerTimeWaitMs DcTestQuickModeAppendResult DcTestForClientServerModeQualityForAntennaCalcMode DcTestForClientServerModeSuspendForBackgroundEnable RoutingTokenEnable OnlineSystem MultiplaySessionRecvThreadReceiveTimeoutUs P2P_ADHOC_BLE_LOW_LEVEL DelayBasedRecoveryEnable RtoEstimatorRttEwmaDeviationSafety

OFFSET=0x9c6b15 TERM=Turn
CONTEXT=putDelayBufferSizeRecentBasicStatisticsMaxSize LatencyWarningLv1ConditionQueueingSizeThreshold MinCorrection CorrectionRiseDeterminationNotReadyForCommandDeltaCountThresholdLow EnableManufactureModelName TurnBufferCriticalConditionTimeCoef TurnNetworkIoReconnectServerTimeWaitMs DcTestQuickModeAppendResult DcTestForClientServerModeQualityForAntennaCalcMode DcTestForClientServerModeSuspendForBackgroundEnable RoutingTokenEnable OnlineSystem MultiplaySessionRecvThreadReceiveTimeoutUs P2P_ADHOC_BLE_LOW_LEVEL DelayBasedRecoveryEnable RtoEstimatorRttEwmaDeviationSafetyCoefficient FecQueueMediaSpecificRed

OFFSET=0x9da4f9 TERM=Turn
CONTEXT=MultiplayStatistics MatchCommandLatencyInMatchCommandActiveRecentBasicStatisticsMaxSize PredictKeepBufferSizeFromNetworkDelayEnable CorrectionRiseThresholdHigh UERHIThreadAffinityMask ListenerWorkerCriticalDelayThreshold Network DscpEnable TurnNetworkIoPingIntervalMs DcTestForClientServerModeRecommendedRegionMode AccessLineTesterTimeoutTimeMs Session UseTickForIndicatorDisplay -> Requested stun method. (REFRESH_REQUEST) O573_CR_REQ |->> [ %s ][ %d bytes ] urn:schemas-upnp-org:service:WANPPPConnection:1 urn:schemas-upnp-org:service:WANIPv6FirewallControl:1 FF05::C friendlyName "serviceType":"%s"

OFFSET=0x9e97ba TERM=Turn
CONTEXT=_3_0_inside_y2_000_sidle_l kick_short_3_0_inside_y2_045_sidle_l gkmovelow_backslant_3_3 gkunderthrow_3_0_near_cancel gkmovenear_front_sidestep_4_1_090 gkmovenear_HeisouBackSlant_0_3 kick_long_3_0_y0_stagger_l_000_down gkmovenear_HeisouFrontTurn_4_4_090 feint_kick_notouch_0_0_000_y0_toe_ver24 gkprejump_riseup_othersideS3 gkrise_faceupslow_0_0_000_a gkrise_faceup_0_0_090 gkrise_sideways_catch_0_0_000 gkscoopout_lie_s02_0_0_y02_090_otherside head_y07_0_0_090_clear_strong_v2 head_y09_shoot_3_0_090 idle_0_1_walk_045 dodge_2_2_090_slideback_y05_act087 kick_long_0_0_inside_y0_000 kick_long_0_0_instep_y0_

OFFSET=0x9efb2b TERM=Turn
CONTEXT=icense SA_V1 A1_P1 A1_PCR A1_PDB A1_PPB A1_PSG A1_PZB B1_P0A EP JiPortNokori Cheer CallTarget CheckNarrowMargin CheckShootTypeMatchStatistics CheckConditionForSASdConfig Numeric ObjectTouchKind CompeStageKind ButtonStatus DirectingDemoType TurnoverVariousData FeintVariousData TOUCH CHANGE_OUT PK SIDE_SCORED SIDE_HOME NEXT_EX VAITAL KNOCKOUT_ROUND_IS_CLOSE LANG_ENG LANG_ENTER PROTEST SCENE_ENTRY RANGE_ENTRY_HA_AUDIENCE NOW AREA_A0 CUP_ITA_SP CUP_BEL_SP LG_ENG1 LG_ENG2 LG_DNK LG_PEU INT_PRE_AFRICA PLAYOFF_D2_JPN THROUGHPASS_SUCCESS TACKLE_SUCCESS OVER_LASTLINE BY_GK SPEED STRONGER_HAND OUT_RIGHT NUM

OFFSET=0xa007ee TERM=Turn
CONTEXT=EM CMD_RESET_MYCLUB_CAREERPLAN CMD_SEND_NOTICE CMD_SET_USER_PROFILE invitedIgnoreAlertInvalidInvitation Online/Invite/ProcessResetInitInvite OutsideCurler 08 27 pl http:// RxPacketLossRateRecentBasicStatisticsMaxSize PeriodicalBackupEnable TurnReconnectWaitTimeMs ChangeoverToP2pFromBufferCriticalConditionTimeWaitMs DcTestUdpStickyAddressShortTimeoutMs DcTestOutlierRateUpper VoiceChatEnable PpsLimit Stale nonce. (error code = xb is_fix ACTIVENETWORK:UNKNOWN PASSWORD RESPONSE_ORIGIN INTEGRITY SESS_ID urn:schemas-upnp-org:service:WANIPv6FirewallControl ,"deviceType":"%s","friendlyName":"%s","manufac

OFFSET=0xa00d5a TERM=Turn
CONTEXT=E_SITUATION LATENCY_NTL_PUNCHING_RETRY GAMRERELAY_MEASUARE_RESULT_AT_MATCHING MEMPEAK_RENDER_TARGET_POOL_SIZE MEMPEAK_MATCH_FLOW_KIND ADDRV6_CHANGED _DECODE_ SessionImplTry getOriginalJson getPricingPhases isProductDetailsSupported CmdWatchTurnAddressData.php OnlineServiceEligibilityCheckTask ETH 100BASE_HALF EKH %4d-%02d-%02dT%02d:%02d:%02dZ ue4.http.proxy.proxyHost jp/konami/android/common/GetThermalStats grpc.http2.max_pings_without_data grpc.experimental.tcp_max_read_chunk_size grpc.optimization_target grpc.enable_http_proxy api !ran_hijacking_interceptor_ G:/PES22HC/Dev-600Series/Source/Share

OFFSET=0xa133be TERM=Turn
CONTEXT=shing ()[B P2P_ADHOC_UNKNOWN_HIGH_LEVEL TxBpsRecentBasicStatisticsMaxSize CorrectionRiseDeterminationTimeMsThresholdLow AppYieldIdleThreadResponseThreshold Xiaomi/M2103K19C|Xiaomi/M2101K7AG|Xiaomi/M2101K7AI P2pBufferCriticalConditionTimeMs TurnNetworkIoMigrateTimeWaitMsMax TurnNetworkIoEwmaPenaltySmoothCoef DcTestPingConnectionTimeoutMs DcTestQuickMode1NumPing DcTestOutlierMinNum NetworkTesterDegradationThreshold RecvInHeaderOverheadLength MinPps RtoEstimatorSrttSmoothCoefficient MatchRecvCommandBufferSize OutOfPlayTimeoutMs Unknown mode. (mode = CMD_SYNC_COOP_PLAYER_DATA FROM NTL 1.17.1-Android 

OFFSET=0xa133e0 TERM=Turn
CONTEXT=LEVEL TxBpsRecentBasicStatisticsMaxSize CorrectionRiseDeterminationTimeMsThresholdLow AppYieldIdleThreadResponseThreshold Xiaomi/M2103K19C|Xiaomi/M2101K7AG|Xiaomi/M2101K7AI P2pBufferCriticalConditionTimeMs TurnNetworkIoMigrateTimeWaitMsMax TurnNetworkIoEwmaPenaltySmoothCoef DcTestPingConnectionTimeoutMs DcTestQuickMode1NumPing DcTestOutlierMinNum NetworkTesterDegradationThreshold RecvInHeaderOverheadLength MinPps RtoEstimatorSrttSmoothCoefficient MatchRecvCommandBufferSize OutOfPlayTimeoutMs Unknown mode. (mode = CMD_SYNC_COOP_PLAYER_DATA FROM NTL 1.17.1-Android Connect FF02::C <SOAP-ENV:Envelope

OFFSET=0xa15457 TERM=Turn
CONTEXT=B_E94 SA_C_NMB02 SA_C_NMB45 SA_C_NMB65 se_list.xml DevelopData/soundScript/develop/Script/Xml_Mobile/Common/ConvertList.xml A1B1_PMB %s_%s_%s%06d_%02d NodeType SetOneCallFlag CheckActAreaForFuturePosBall CheckFreePlayerTargetArea CheckTurnEndTrigger CheckPlayerFeintKind CheckPassTargetPointDist CheckPlayerDataMyClub FoulKind DribbleMode SpConditonPlayerVoiceForSd InjuryPart ShootResultVariousData SetSoundTarget END_RETIRE_BL 1ST_2ND EX USER RANGE_ENTRY_AND_CLAP STADIUM_ENTER 07_1 AREA_BZ AREA_CZ SIDE_MID FIELD_RIGHT QUALIFY_1ST_MATCH CUP_NAME CUP_POR CUP_MEX2 CUP_COL CUP_KONAMI LG_SAU LG_D2 I

OFFSET=0xa1fa6f TERM=Turn
CONTEXT=ControllerKeyJustPressed bAltEnterTogglesFullscreen GetInstancesOverlappingSphere InterpEdSelKey PawnClass InterpLookupTrack Key_IsVectorAxis PointerEvent_GetPointerIndex EMIDCreationFlags And_Int64Int64 Atan2 DateTimeFromString FCeil FixedTurn GetTotalMinutes Less_FloatFloat LessEqual_Int64Int64 LessEqual_IntInt MakeColor Matrix_ContainsNaN MinimumAreaRectangle Multiply_MatrixFloat NegateVector NormalizedDeltaRotator Percent_ByteByte Quat_GetAxisY Quat_IsFinite Quat_RotateVector Round64 Subtract_IntPointInt Vector_Assign VSizeXYSquared WeightedMovingAverage_FRotator InBoxMin bRandom Conv_MatrixTo

OFFSET=0xa25e71 TERM=Turn
CONTEXT=um_name ()J P2P CongestionControlWindowSizeLimitRecentBasicStatisticsMaxSize DequeueHzAccelerationMaxRate BufferKeeperEnableForPlatform MaxCorrection CorrectionFallDeterminationNotReadyForCommandDeltaCountThresholdLow m_asymmetricInputDelayTurnDisconnectStatusEnable TurnBufferCriticalConditionTimeAddConst TurnNetworkIoCheckDegradationThresholdRttCount DcTestForClientServerModeSuspendForBackgroundTimeMs Reordering DelayBasedLimiterLimiterJudgementTimeMs FecQueueParityEncoderEnablePadding ActualMatchHzFatalConditionHzThreshold NoMoveOperationCheckerKindForStrikeArena IsEnabledDisplayingLinesmanAndRe

OFFSET=0xa25e8c TERM=Turn
CONTEXT=ontrolWindowSizeLimitRecentBasicStatisticsMaxSize DequeueHzAccelerationMaxRate BufferKeeperEnableForPlatform MaxCorrection CorrectionFallDeterminationNotReadyForCommandDeltaCountThresholdLow m_asymmetricInputDelayTurnDisconnectStatusEnable TurnBufferCriticalConditionTimeAddConst TurnNetworkIoCheckDegradationThresholdRttCount DcTestForClientServerModeSuspendForBackgroundTimeMs Reordering DelayBasedLimiterLimiterJudgementTimeMs FecQueueParityEncoderEnablePadding ActualMatchHzFatalConditionHzThreshold NoMoveOperationCheckerKindForStrikeArena IsEnabledDisplayingLinesmanAndRefereeOnMobile unique_lock::

OFFSET=0xa25eb4 TERM=Turn
CONTEXT=csMaxSize DequeueHzAccelerationMaxRate BufferKeeperEnableForPlatform MaxCorrection CorrectionFallDeterminationNotReadyForCommandDeltaCountThresholdLow m_asymmetricInputDelayTurnDisconnectStatusEnable TurnBufferCriticalConditionTimeAddConst TurnNetworkIoCheckDegradationThresholdRttCount DcTestForClientServerModeSuspendForBackgroundTimeMs Reordering DelayBasedLimiterLimiterJudgementTimeMs FecQueueParityEncoderEnablePadding ActualMatchHzFatalConditionHzThreshold NoMoveOperationCheckerKindForStrikeArena IsEnabledDisplayingLinesmanAndRefereeOnMobile unique_lock::lock: already locked ktc-0.0.0 Responded

OFFSET=0xa3214d TERM=Turn
CONTEXT=othWorldChannels Fly StreamLevelIn ScreenShotDescription GoString EditProfiles EComponentCreationMethod IndexChar LinearBreakThreshold PossessedPawn ReceivePossess bNewMoveInput MaxTime GetCurvePosition ImportKeyField ReceiveOnActivate BaseTurnRate ObjReferences CVars EGrammaticalNumber::Singular EGrammaticalNumber ShadowDistanceFadeoutFraction ShadowAmount MaxOutput ParamMode EDVMF_Mirror EDVLF_YZ MinValueVec MacroGraph ENodeAdvancedPins::NoPins bIsConst PS_CameraEffect ScreenMessage StatColorMapping ActiveNetDrivers bEnableEditorPSysRealtimeLOD bEnableOnScreenDebugMessagesDisplay VMI_StationaryL

OFFSET=0xa3850c TERM=Turn
CONTEXT=agueComRecord UserCompeRecordInfoWork CgkI2KWEy_UIEAIQVQ TaskGetBlockList TaskGetCoinUseInfo TaskLeagueMainMenuCheckBeforeMatch G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineMode\Task\Match\OnlineModeTaskCheckCheat.cpp CmdGetTurnServerList m_selectedPlayerArray m_subLevel m_changeWeather m_ball CustomStadiumList2.bin %08x %s_b02 %s_b03 %s_m06 RisingShot ad_user_data jp ERR_PLATFORM_SERVICE DcTestForClientServerMode CongestionControlBpsRecentBasicStatisticsMaxSize MatchCommandDequeueHzRateInMatchCommandActiveRecentBasicStatisticsMaxSize MaxBufferSize MatchControlInfoNotifyIntervalTim

OFFSET=0xa386a8 TERM=Turn
CONTEXT=stForClientServerMode CongestionControlBpsRecentBasicStatisticsMaxSize MatchCommandDequeueHzRateInMatchCommandActiveRecentBasicStatisticsMaxSize MaxBufferSize MatchControlInfoNotifyIntervalTimeUs BufferSizeLimitLow OPPO/CPH1909 ChangeoverToTurnBufferCriticalConditionTimeMsThreshold DcTestQuickMode3UdpSendIntervalMs DcTestForClientServerModeRetryTimeoutMs MultiplaySessionGameThreadWatchdogTimerTimeoutUs ObservePlaybackMaxRecvDataQueueSize KeyExchangeTimeoutUs unique_lock::lock: references null mutex Opened. (ConnectionId = Bind channel retry limit exceeded. (limit = CMD_REVISION_CHECK entry_check

OFFSET=0xa388f7 TERM=Turn
CONTEXT=K entry_check_sum CMD_SYNC_MATCHPLAN_DATA_LITE is_pf_play_history_key_set NtlUpdateThread LIFETIME REALM REQUESTED_ADDRESS_FAMILY INDICATION LOCATION SOAPAction: "%s#%s" modelName udp "%s":[ [ %d ] DeletePortForwarding Fail. ${"%s":%d} ## Turn Status ${"rtt:":%d} E_ADDRINUSE ALLOC_TURN_PORT_ERROR FREE_TURN_PORT_COMPLETE ALLOC_TURN_CHANNEL_BINDING_COMPLETE START_SERVER_UDP_SESSION_COMPLETE KEEPALIVE_FAKE PEER_TURN %63s%X%X%X%d%d%d%X%d%d%d interval_factor PS5 timeout widevine_id use_cronet MODELNAME_PEERS NUM_LOCAL_GUESTS_BEGIN_MATCH MATCH_CONDITION IDELAY_BUF_SIZE_STANDARD_VALUE_ MATCH_STOP_COUN

OFFSET=0xa38c30 TERM=Turn
CONTEXT=Y_MODE_CONNECT_MODE_MULTIPLAY MAIN_THREAD_LAST_UPDATED (Ljava/lang/String;[Ljava/lang/String;)V (Lcom/android/billingclient/api/BillingResult;Lcom/android/billingclient/api/Purchase;)V gps_adid steam_item_id CmdVerifyUserCanBuy.php CmdWatchTurnAddressData ; EHH EKF XSX sun EnableBroadcasting grpc.service_config hooks_[static_cast<size_t>( experimental::InterceptionHookPoints::PRE_SEND_MESSAGE)] a.clock_type == b.clock_type b.tv_nsec >= 0 Cancelled grpc_status "Out of memory" getsockopt refcount %s=%s gpr_atm_no_barrier_fetch_add(&fd->refst, n) > 0 pipe creation failed (%d): %s setsockopt(TCP_NODE

OFFSET=0xa4573d TERM=Turn
CONTEXT=SoftClassReference GetObjectFromPrimaryAssetId GetPlatformUserDir IsStandalone SphereTraceMulti PlaneCoordinates Resolutions ValidTypes InitialStartDelay ToPositiveInfinity OutText PolyglotData ActorStats bAttached LevelScriptActor bAffectsTurning OnLevelShown SetBrightness bUseIESBrightness VolumetricScatteringIntensity SetIntensityUnits MDR_None bNormalCurvatureToRoughness bIsSky TCC_Blue CMOT_MAX CustomOutput CustomInput TDOF_MAX FunctionInput_Vector3 Coordinates SceneTextureId StaticComponentMaskParameterValues bOverride_OpacityMaskClipValue SourceB ForceDuration TextureSizingType_UseAutomatic

OFFSET=0xa51ec4 TERM=Turn
CONTEXT=andTouchFlick/CommandTouchFlickAdvanced_1_Move.CommandTouchFlickAdvanced_1_Move_C /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_3_PassAndCrossRun.CommandTouchFlickAdvanced_3_PassAndCrossRun_C EdgeTurn TeamInfo Icon_None IconArrow match_topmenu onlineNext coop_commendation User_%d Text_%d GraphType_90 UiLock Receive_First_0_100 SE_SYS_DECIDE CampaignPassCollectionPartsTouchableWidget Img_Plate_Bonus NamedSlotCustom_2Spots /Game/Assets/ui/Data/Widget/Objective/Alert/AlertCampaignPassMap/AlertCampaignPassMap.AlertCampaignPassMap_C CancelAcquireAlertCallback

OFFSET=0xa84f55 TERM=Turn
CONTEXT=E out of date ! P2P_ADHOC LatencyCriticalConditionQueueingSizeThreshold LatencyFatalConditionDeterminationTimeUs CorrectionRiseDeterminationTimeMs CorrectionRiseWaitTimeMs UERHIThreadPriority AppYieldUeThreadLowPriority CheckSocketDisabled TurnModeP2pSendIntervalMs TurnNetworkIoDegradedByDisconnectEnable MultiplaySessionStrategyIoBufferRecvSize FecQueueParityEncoderMaxBufferLength ChannelReceiveBufferMaxBufferLength ActualMatchHzConditionDeterminationEnable ActualMatchHzWithInactiveConditionDeterminationEnable turn_mode Unknown error code. (error code = Wrong credentials. (error code = CMD_SIDE_

OFFSET=0xa84f6f TERM=Turn
CONTEXT=LatencyCriticalConditionQueueingSizeThreshold LatencyFatalConditionDeterminationTimeUs CorrectionRiseDeterminationTimeMs CorrectionRiseWaitTimeMs UERHIThreadPriority AppYieldUeThreadLowPriority CheckSocketDisabled TurnModeP2pSendIntervalMs TurnNetworkIoDegradedByDisconnectEnable MultiplaySessionStrategyIoBufferRecvSize FecQueueParityEncoderMaxBufferLength ChannelReceiveBufferMaxBufferLength ActualMatchHzConditionDeterminationEnable ActualMatchHzWithInactiveConditionDeterminationEnable turn_mode Unknown error code. (error code = Wrong credentials. (error code = CMD_SIDE_SELECT CMD_SYNC_MATCHPLAN_

OFFSET=0xa85156 TERM=Turn
CONTEXT=le turn_mode Unknown error code. (error code = Wrong credentials. (error code = CMD_SIDE_SELECT CMD_SYNC_MATCHPLAN_DATA_FULL [cnt: NONCE SUCCESS_RESP SoapAction: "%s#%s" specVersion NewRemoteHost </SOAP-ENV:Body></SOAP-ENV:Envelope> ${"TurnEvent":"%s(0x%08x)"} G_TIMEOUT E_MUTEX_PERM E_INVALID_OPS UPNP_DELETE_PORT_FORWARDING_MISS_MATCH ADD -%s command_adaptive_retry link_down_check_enable xbx R_VARIANCE NETWORK_STATUS RX_BPS_ EXECUTED_COMMAND_COUNT SEND_COMMAND_DROP_COUNT_MCACTIVE MATCH_STOP_COUNT_SELF_BUF_EMPTY RECEIVED_FROM_UNKNOWN_PEER_LENGTH IP_ADDRESS_ICMP_BEGIN_TEST TURN_QUALITY_BASE_RTT_

OFFSET=0xaaa382 TERM=Turn
CONTEXT=pstep_000_3_3_y0_sole_3 demo_gk_glad_23 demo_gk_appeal_3 throw_under_0_0_quick blockfront_forecast_0_0_y03 blockside_forecast_3_0_y00 demo_gk_glad_lie_18 demo_appeal_2_1_045_2 demo_cheer_at090_2 rouletteribery_2_3_l dribble_deprived_0 [goalTurn]nowFrame=%d , endFrame=%d [GoalMove] %s Will Contact goal net Bound Info-> EachTime: [Command] ControlMode [%s] (cross & exist other follow player%d) [Command] ControlMode [%s] (enemy pass touch timer under 1.5sec but nextkeep and follow) [Command] ControlMode [%s](team follow player) [Command] ControlMode [%s] (setplay & not restart side & not even

OFFSET=0xaab641 TERM=Turn
CONTEXT=skUserActionGetGameplanInfo TaskSetAvatar 0000_f04_%d_ 0000_m05_%d_ Sombrero LongRangeShooting PenaltySpecialist ERR_GIVE_UP AddRequestHeader (Ljava/lang/String;Ljava/lang/String;)V application/octet-stream SetFileParam DcTestVer0 P2pModeTurnSendIntervalMs TurnEnableDualRouteModeTime TurnNetworkIoConnectionTimeoutMs TurnNetworkIoRttSuddenChangeThreshold DcTestForClientServerModeAutoRetryLossRateThreshold MultiplaySessionStrategyIoBufferSendSize CsResetUdpSocketIntervalMs DcTestWebSocketClientEnableIgnoreCertCnInvalid NetworkTesterEnable ObservePlaybackRecvMatchCommandTimeoutMs LinkTableSize Cong

OFFSET=0xaab654 TERM=Turn
CONTEXT=planInfo TaskSetAvatar 0000_f04_%d_ 0000_m05_%d_ Sombrero LongRangeShooting PenaltySpecialist ERR_GIVE_UP AddRequestHeader (Ljava/lang/String;Ljava/lang/String;)V application/octet-stream SetFileParam DcTestVer0 P2pModeTurnSendIntervalMs TurnEnableDualRouteModeTime TurnNetworkIoConnectionTimeoutMs TurnNetworkIoRttSuddenChangeThreshold DcTestForClientServerModeAutoRetryLossRateThreshold MultiplaySessionStrategyIoBufferSendSize CsResetUdpSocketIntervalMs DcTestWebSocketClientEnableIgnoreCertCnInvalid NetworkTesterEnable ObservePlaybackRecvMatchCommandTimeoutMs LinkTableSize CongestionControlAlgori

OFFSET=0xaab670 TERM=Turn
CONTEXT=f04_%d_ 0000_m05_%d_ Sombrero LongRangeShooting PenaltySpecialist ERR_GIVE_UP AddRequestHeader (Ljava/lang/String;Ljava/lang/String;)V application/octet-stream SetFileParam DcTestVer0 P2pModeTurnSendIntervalMs TurnEnableDualRouteModeTime TurnNetworkIoConnectionTimeoutMs TurnNetworkIoRttSuddenChangeThreshold DcTestForClientServerModeAutoRetryLossRateThreshold MultiplaySessionStrategyIoBufferSendSize CsResetUdpSocketIntervalMs DcTestWebSocketClientEnableIgnoreCertCnInvalid NetworkTesterEnable ObservePlaybackRecvMatchCommandTimeoutMs LinkTableSize CongestionControlAlgorithm MaxSendOctetLengthPerPac

OFFSET=0xaab691 TERM=Turn
CONTEXT=gRangeShooting PenaltySpecialist ERR_GIVE_UP AddRequestHeader (Ljava/lang/String;Ljava/lang/String;)V application/octet-stream SetFileParam DcTestVer0 P2pModeTurnSendIntervalMs TurnEnableDualRouteModeTime TurnNetworkIoConnectionTimeoutMs TurnNetworkIoRttSuddenChangeThreshold DcTestForClientServerModeAutoRetryLossRateThreshold MultiplaySessionStrategyIoBufferSendSize CsResetUdpSocketIntervalMs DcTestWebSocketClientEnableIgnoreCertCnInvalid NetworkTesterEnable ObservePlaybackRecvMatchCommandTimeoutMs LinkTableSize CongestionControlAlgorithm MaxSendOctetLengthPerPacket DefaultCongestionWindowSize C

OFFSET=0xaabc22 TERM=Turn
CONTEXT=_SETTING INDICATOR_STATS_CSV LATENCY_MODE_ANNTENA_WAIT_QUALITY_CHECK V6_UDP_SOCKET_ERROR RSSI_R_MEAN getResponseCode getDescription getIntroductoryPrice getOfferToken getProduct Number of purchaseHistoryRecords: %d base_coin cmdName CmdSendTurnAddressData.php EHF TNL HOS grpc.enable_deadline_checking xds_client compression op_failure backup_count_ <= INT_MAX %s:%d] %s G:\PES22HC\Dev-600Series\Source\Shared\basic\ext\grpc\grpc\src\core\lib\surface\completion_queue.cc pthread_condattr_init(&attr) == 0 queued_buffers end >= begin G:\PES22HC\Dev-600Series\Source\Shared\basic\ext\grpc\grpc\src\core\lib

OFFSET=0xabcfe1 TERM=Turn
CONTEXT=able/bin/Parametricblendtable.bin Reserve SetLyaer: %s m(%d), duration(%.2f) layerMaskType(%d) [FaceHand] EyeBlink( true ) = %f [SetUpperBodyArmBoneAdjust] IsStop[%d] IsGoto[%d] IsStop[%d] IsLoop[%d] IsAcceleration[%d] IsDecelerate[%d] IsTurn[%d] IsDeepTurn[%d] IsFarTouch[%d] InSpeed[%d] OutSpeed[%d] actionKind = %d [ActionTrapAdjust] IsPossibleToAdjust false [TrapBetween] ballDist = %.2f ballDist = %.2f demo_miss_thumbsup_0_1 demo_coop_inspire_2 demo_pfm_cornerF_kick_l demo_pfm_jumpunderguts_3_3_l demo_goal_recorder_loop goalkick_instep_r puntkick_side_0_0_fast2 linesman_4_4 linesman_tur

OFFSET=0xabcff0 TERM=Turn
CONTEXT=tricblendtable.bin Reserve SetLyaer: %s m(%d), duration(%.2f) layerMaskType(%d) [FaceHand] EyeBlink( true ) = %f [SetUpperBodyArmBoneAdjust] IsStop[%d] IsGoto[%d] IsStop[%d] IsLoop[%d] IsAcceleration[%d] IsDecelerate[%d] IsTurn[%d] IsDeepTurn[%d] IsFarTouch[%d] InSpeed[%d] OutSpeed[%d] actionKind = %d [ActionTrapAdjust] IsPossibleToAdjust false [TrapBetween] ballDist = %.2f ballDist = %.2f demo_miss_thumbsup_0_1 demo_coop_inspire_2 demo_pfm_cornerF_kick_l demo_pfm_jumpunderguts_3_3_l demo_goal_recorder_loop goalkick_instep_r puntkick_side_0_0_fast2 linesman_4_4 linesman_turn_4_4 seamless_

OFFSET=0xabe9f7 TERM=Turn
CONTEXT=vMemory jp/konami/android/common/Cronet TxPpsRecentBasicStatisticsMaxSize BufferSizeLimitHigh ListenerWorkerThreadAffinityMask UEGameThreadAffinityMask AppYieldLowPriorityTimeoutMs OPPO/CPH2127|OPPO/CPH2131|OPPO/CPH2133|OPPO/CPH2139 P2pModeTurnSendEnable TurnNetworkIoDegradedJudgementEnable AccessLineTesterAutoTestReceiveIdleTimeMsThreshold AccessLineTesterMode ObservePlaybackReadTimeoutMs P2P_ADHOC_BLE_HIGH_LEVEL P2P_ADHOC_LAN_HIGH_LEVEL P2P_ADHOC_LAN_GIVE_UP_QUICKLY_LEVEL ScalableTcpAlpha ParityDecoderEnablePadding Mobility forbidden. (error code = CMD_MATCH_SETTINGS revision param_check_sum SI

OFFSET=0xabea06 TERM=Turn
CONTEXT=mi/android/common/Cronet TxPpsRecentBasicStatisticsMaxSize BufferSizeLimitHigh ListenerWorkerThreadAffinityMask UEGameThreadAffinityMask AppYieldLowPriorityTimeoutMs OPPO/CPH2127|OPPO/CPH2131|OPPO/CPH2133|OPPO/CPH2139 P2pModeTurnSendEnable TurnNetworkIoDegradedJudgementEnable AccessLineTesterAutoTestReceiveIdleTimeMsThreshold AccessLineTesterMode ObservePlaybackReadTimeoutMs P2P_ADHOC_BLE_HIGH_LEVEL P2P_ADHOC_LAN_HIGH_LEVEL P2P_ADHOC_LAN_GIVE_UP_QUICKLY_LEVEL ScalableTcpAlpha ParityDecoderEnablePadding Mobility forbidden. (error code = CMD_MATCH_SETTINGS revision param_check_sum SIGN CHANNELBIND 

OFFSET=0xabee73 TERM=Turn
CONTEXT=ST_L1_MCACTIVE MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L5_MCACTIVE COMMUNICATION_TIME LATENCY_TURN_GET_TURN_ADDRESS_MAX GPU_MANUFACTURER NETWORKINFO EVENT_ID " getIntroductoryPriceCycles getItemDetails EMPTY_RECEIPT authorization_code CmdGetTurnAddressData.php M5 GDK getTxBytes grpc.http2_scheme grpc.keepalive_timeout_ms grpc.server_handshake_timeout_ms false && "It is illegal to call GetRecvMessage on a method which " "has a Cancel notification" %Y-%m-%dT%H:%M:%S !cqd->shutdown.Load(grpc_core::MemoryOrder::RELAXED) wsa_error Error %p is full, dropping "%s":"%s"} G:\PES22HC\Dev-600Series\Source\Sha

OFFSET=0xacf41b TERM=Turn
CONTEXT=rob stopSpeed subValue100percent objectData paraMinSpeedRate decMaxSpeedR rootAccWeight trapStopThinkStrongerFoot normal_dy ballRouteAdjustMoveFrame passgetSpeedRate searchTest2 stickTest1 ballControlWeekFootDownLimit dashOfRun stopTrapStopTurnAngle startSugorokuKind offenceZposiAdjustDist player_count_height HAnmWC cpk_dat/ demo/mob/ skel.frig sk IsAnyDemoSequenceLoop %d %s PlayDemoSequenceWithOffset %d %s %s G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\GameMode\GameModeMatchListenerMatch.cpp Def_Game_Non_Parameter_Assert match_online es-EA ja CameraPersonListener myclub acl_pes acl_f MatchBeg

OFFSET=0xad12c3 TERM=Turn
CONTEXT=ame\Online\OnlineSystem\Api\OnlineSystemApiManagerver3.cpp pes-custom-encrypt verify HttpClientImpl2 P2P_LOW_LEVEL InputDelayBufferSizeStandardValueRecentBasicStatisticsMaxSize QueueReducesInMatchActiveMarginCoefficient AsymmetricInputDelayTurnDisconnectedModeEnable DoesBlockSocketError ChangeoverPeerReceiveIdleTimeMsThreshold DcTestPingTimeoutMs DcTestNumPing MultiplaySessionDaemonStatisticsIoBufferSize WebSocketClientConnectRetryIntervalMs DcTestWebSocketClientEnableIgnoreUnknownCa MultiplaySessionWatchdogTimerTimeoutUs AccessLineTesterPrivateNetworkQualityPoorThreshold ChannelTransferMode FecQu

OFFSET=0xad1771 TERM=Turn
CONTEXT=RTT_EWMA SEND_TO_NET_INFO_MAX_SEND_ATTEMPT_INTERVAL APP_YIELD_STATS_INACTIVITY_TIME_MS BPS_SEND_ RX_LOSS_RATE_MEAN Not Implement <unsupported field> getQuantity getInventory xb1_store_id application_user_name CmdSendAuthorizationCode CmdGetTurnAddressData CmdSendAdjustParam LINK_DOWN AND grpc.max_connection_age_grace_ms grpc.max_metadata_size grpc.enable_retries grpc.channel_pooling_domain pick_first queue_pluck pos < interceptors_.size() No payload !started_ GRPC_SLICE_LENGTH(slice_) <= INT_MAX Illegal value '%s' specified for environment variable '%s' cq_end_op_for_pluck(cq=%p, tag=%p, error=%s,

OFFSET=0xaf07dd TERM=Turn
CONTEXT=oCaptureProtocol FrameDelta AnimStreamable_GetAnimationPose RaycastTest GeomSweepSingle LightingResults SDebugCanvas OnTakeRadialDamage FAudioDevice::Init DefaultPawn_MoveForward DFAtlasPercentageUsage ZeroLengthProjectionWarning Spectator_Turn IndirectLightingCache ForceFeedbackRadius Grid Paper2DSprites MeshUVDensityAccuracy FStaticMeshStaticLightingMesh_IntersectLightRay TimelineComponent ForceNetUpdate GetComponentByClass ReceiveDestroyed NewRelativeScale Deactivate AttributeBlendModes GraphBlendOptions OutputPoseNodeProperty AnimGraphBlendOptions ERootMotionMode::RootMotionFromEverything GetI

OFFSET=0xaf1257 TERM=Turn
CONTEXT=ormalOffset BLEND_Opaque EAttachLocation::KeepWorldPosition EAttachLocation RotationQuantizationLevel MinimumDamage bUseHighPrecisionTangentBasis BaseNonRenderedUpdateRate bDebugMode bUseEmissiveForStaticLighting FogCutoffDistance MaxSpeed TurningBoost Ascent ForceFeedbackEffect bPlayWhilePaused HandleNetworkError AbortMatch Say InitStartSpot ExitingController PlayerStateClass ReplaySpectatorPlayerControllerClass AnnounceAccessibleString GetActorOfClass HasLaunchOption PredictParams OutHit OutPathPositions OverrideGravityZ OwningActor GetShadingQuality LastConfirmedFullscreenMode InputVectorAxisHa

OFFSET=0xaf52ee TERM=Turn
CONTEXT=um/demoarea_st091.json DevelopData/common/match/constant/stadium/demoarea_st099.json DevelopData/common/match/constant/sugoroku/Sugoroku_pk.json L_BackCam_spawn technical_area_home boundToRotationAddRateY frictionRollRateMin goal_or_assist TurnData limitZRate heightForDistMaxParaMax heightForDistMaxSkill autoRecieveSpeedAddDistMin lobHeightDistMax routeWeight pressure inputR2 nextPlayEnable angleAddValue injectionAngleMax passgetLineDiff runTrapStopTurnAngle reactionBallSpeed adjustFwLine checkBaseDist cornerkickDefenceMFWidth dfCoverEnable freeKickAdjustRateX_MF slideKind demo/prop/ SetPos match

OFFSET=0xaf53c3 TERM=Turn
CONTEXT=RollRateMin goal_or_assist TurnData limitZRate heightForDistMaxParaMax heightForDistMaxSkill autoRecieveSpeedAddDistMin lobHeightDistMax routeWeight pressure inputR2 nextPlayEnable angleAddValue injectionAngleMax passgetLineDiff runTrapStopTurnAngle reactionBallSpeed adjustFwLine checkBaseDist cornerkickDefenceMFWidth dfCoverEnable freeKickAdjustRateX_MF slideKind demo/prop/ SetPos match_training Invalid State : ( es_MX it cpk_dat/common/anime/FoxAnim/goal_r.geom SetBasePos SetPropsVector BallPersonListener cpk_dat/common/match/constant/constant_tutorialMobile.bin MatchAnalyzeListener MatchEndLi

OFFSET=0xaf721c TERM=Turn
CONTEXT=s_f04_max_lim us LowCommandApi Def_Online_gRPC_debug_root_ca dec2 SendRequest GetReceivedDataLength DcTestWorker SendBufferLimitRateLow BufferingExecutionRateDropStateInCritical QueueReducesInMatchActiveMarginBufferSize AsymmetricInputDelayTurnMaxThreshold NetworkIoVersion DcTestOutlierRateLower DcTestForClientServerModeRecommendedRegionThreshold DelayBasedRecoveryRecoveryJudgementTimeMs FecQueueParityEnable CommandLackInPlayTimeoutMs Change internal state. ( CMD_READY_FLAG net_link_type 0.0.0.0%s0 PADDING | |->> [ %s ][ %d ] REF_XADDR Invalid ErrorResp. Host: %s major RemoteHost InternalClient G

OFFSET=0xb16707 TERM=Turn
CONTEXT=ring bEnableTextureStreaming PathTracerSamplePerPixel GetCurrentFrameMetrics OnCanFinalize CMC_ApplyRepulsionForce MoveComponentTime WorkerThreadTickTime PhysXGeneric FireImpulseOverlap RenderAssetStreaming DebugCamera_Unselect DefaultPawn_Turn PropertySetFailedWarning EventWait/EndPhysics G:/UE4.26_eFB/Base/Engine/Source/Runtime/Engine/Classes/GameFramework/LocalMessage.h NetworkOutgoing BillboardSprites CameraFrustums LightInfluences Wireframe OutputMaterialTextureScales MediaPlanes DebugHUD ButtonReleased EActorUpdateOverlapsMethod::NeverUpdate EnableInput K2_DestroyComponent OnRep_IsActive Set

OFFSET=0xb1da2d TERM=Turn
CONTEXT=REGION_PRIORITY GAME_SERVER_NAME DOWNLOAD_SERVER_STATS_SEND_URL GAME_SERVER_STATS_RECV_URL inapp getSubscriptionPeriod getPurchaseState getObfuscatedAccountId nativeOnConsumeFinished limit_buy_count enable_dual_price_system tls_port ConnectTurnTask FIREWIRE getRssi (Landroid/content/Context;)I grpc.max_receive_message_length grpc.mobile_log_context cds_lb call_error serializer_(msg_).ok() Completion queue next failed: %s pthread_cond_init(cv, &attr) == 0 b.clock_type == GPR_TIMESPAN raw_bytes G:/PES22HC/Dev-600Series/Source/Shared/basic/ext/grpc/grpc/src/core/lib/iomgr/error.h BACKUP_POLLER:%p des

OFFSET=0xb439ae TERM=Turn
CONTEXT=rActionGetUserBannerList %s_b01 KnuckleShot 10 14 19 GetLastErrorExceptionStr DcTestVer1 StopBufferingInCriticalCondition AsymmetricInputDelayModeEnable ListenerWorkerFrameRateControlIntervalMs MaxPayloadLength NetworkIoConnectionTimeoutUs TurnNetworkIoTcpConnectionTimeoutMs TurnNetworkIoDegradedLatencyRatio DcTestNumWorker NetworkTesterPingTimeoutMs PingRequestTimeoutUs LinkUpMode KeyExcahngeRetransmissionTimeoutUs P2P_ADHOC_WIFIDIRECTLAN_LOW_LEVEL P2P_ADHOC_LAN direct_online_turn_mode NetworkQualityIndicator ps f2p RESPONSE_ADDRESS RP_SYNC_POINT |->> [ %s ][ %d ] URLBase TurnInitializedNatType 

OFFSET=0xb439d2 TERM=Turn
CONTEXT=kleShot 10 14 19 GetLastErrorExceptionStr DcTestVer1 StopBufferingInCriticalCondition AsymmetricInputDelayModeEnable ListenerWorkerFrameRateControlIntervalMs MaxPayloadLength NetworkIoConnectionTimeoutUs TurnNetworkIoTcpConnectionTimeoutMs TurnNetworkIoDegradedLatencyRatio DcTestNumWorker NetworkTesterPingTimeoutMs PingRequestTimeoutUs LinkUpMode KeyExcahngeRetransmissionTimeoutUs P2P_ADHOC_WIFIDIRECTLAN_LOW_LEVEL P2P_ADHOC_LAN direct_online_turn_mode NetworkQualityIndicator ps f2p RESPONSE_ADDRESS RP_SYNC_POINT |->> [ %s ][ %d ] URLBase TurnInitializedNatType RevokeConnectivity uds E_NOMEM E_NOT

OFFSET=0xb43b03 TERM=Turn
CONTEXT=ngTimeoutMs PingRequestTimeoutUs LinkUpMode KeyExcahngeRetransmissionTimeoutUs P2P_ADHOC_WIFIDIRECTLAN_LOW_LEVEL P2P_ADHOC_LAN direct_online_turn_mode NetworkQualityIndicator ps f2p RESPONSE_ADDRESS RP_SYNC_POINT |->> [ %s ][ %d ] URLBase TurnInitializedNatType RevokeConnectivity uds E_NOMEM E_NOTFOUND E_UPNP_DEVICE_NOT_FOUND E_TURN_NOT_AVAILABLE UPNP_DISCOVERY_FULL_COMPLETE START_UDP_HOLE_PUNCHING_ADVICE_CANCEL_HAIRPIN jnihelper ] is already registered! ANDROID Windows nsw NATTYPEV6 SEND_COMMAND_DROP_COUNT_BURST_L5 SEND_COMMAND_DROP_COUNT_BURST_L4_MCACTIVE SELF_AUTOMOVE_COUNT_BURST_L2 MATCH_STO

OFFSET=0xb4f5bd TERM=Turn
CONTEXT=ugCamera NewTimeDilation ChildActorClass CustomProfile DuplicatedObjects MeshUVChannelInfo IsLocalController K2_GetPawn WarnIfTimeLimitExceeded FlushStreamingOnGC MultithreadedDestructionEnabled CullDistanceSizePair bIsEventCurve GetCurves TurnAtRate DistanceFieldShadowDistance DistributionParamMode PinId MemberName MemberGuid CONNECT_RESPONSE_MAX FullSearchTitlesArray OnParticleSpawn NewStructName LoadedLevelsForPendingMapChange LocalPlayerClassName ShadedLevelColorationUnlitMaterial LightMapDensitySelectedColor ActiveStructRedirects bLockReadOnlyLevels VMI_MeshUVDensityAccuracy ETickingGroup EMo

OFFSET=0xb559e7 TERM=Turn
CONTEXT=\Multiplay\OnlineSystemMultiplay.cpp MinBufferSize BufferWarningLv1ConditionBufferSizeThreshold ListenerWorkerConfig AppYieldListenerWorkerThreadLowPriority samsung/SM-A307FN|samsung/SM-A307G|samsung/SM-A307GN|samsung/SM-A307GT ChangeoverToTurnReceiveIdleTimeMsThreshold TurnNetworkIoRecentlyRttMaxSize DcTestForClientServerModeMaxRetryTimeoutMs WebSocketClientDisableVerifyHost AccessLineTesterNetworkQualityDegradeCoefficient P2P_ADHOC_WIFIDIRECTLAN_GIVE_UP_QUICKLY_LEVEL P2P_ADHOC_LAN_LOW_LEVEL wss:// G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineSystem\Multiplay\SessionStrategy\Onlin

OFFSET=0xb55a06 TERM=Turn
CONTEXT=y.cpp MinBufferSize BufferWarningLv1ConditionBufferSizeThreshold ListenerWorkerConfig AppYieldListenerWorkerThreadLowPriority samsung/SM-A307FN|samsung/SM-A307G|samsung/SM-A307GN|samsung/SM-A307GT ChangeoverToTurnReceiveIdleTimeMsThreshold TurnNetworkIoRecentlyRttMaxSize DcTestForClientServerModeMaxRetryTimeoutMs WebSocketClientDisableVerifyHost AccessLineTesterNetworkQualityDegradeCoefficient P2P_ADHOC_WIFIDIRECTLAN_GIVE_UP_QUICKLY_LEVEL P2P_ADHOC_LAN_LOW_LEVEL wss:// G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineSystem\Multiplay\SessionStrategy\OnlineSystemMultiplaySessionStrategy

OFFSET=0xb55b81 TERM=Turn
CONTEXT=egradeCoefficient P2P_ADHOC_WIFIDIRECTLAN_GIVE_UP_QUICKLY_LEVEL P2P_ADHOC_LAN_LOW_LEVEL wss:// G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineSystem\Multiplay\SessionStrategy\OnlineSystemMultiplaySessionStrategyP2pFullMeshWithTurn.cpp ] RP_JSON_DATA SEQ MappingTestIB FilteringTestII Allocate GetNonce |->> [ %s ][ %d ][ %s ] extra E_OK E_STUN_TEST_ERROR E_MUTEX_INVAL FREE_TURN_CHANNEL_BINDING_ABORTED ro.build.version.release XX 8.8.8.8 match_session_not_connected_timeout_sec SERVNAMEV6 PLATFORM_PEERS NUM_GUESTS_END_MATCH MCDEQUEUEHZ_RATE_ MATCH_STOP_COUNT_BUF_EMPTY TURN_QUALITY_DEGR

OFFSET=0xb68f08 TERM=Turn
CONTEXT=rkAccessLineTest P2P_HIGH_LEVEL MatchCommandDequeueHzRateRecentBasicStatisticsMaxSize DequeueHzAccelerationMarginBufferSize MatchControlAlgorithm MinKeepBufferSize CorrectionFallDeterminationNotReadyForCommandDeltaCount AsymmetricInputDelayTurnLimitEnable AsymmetricInputDelayTurnSuddenChangeEnable EnableManufactureModelNamePresetType Dscp ScrambleEnable TcpFallbackEnable DcTestQuickModeNumTest ObserveRecordTimeoutMs DisableBufferingControlInSetPlay ImportantKickCommandMustEnable MultiplaySessionRecvSub Refresh retry limit exceeded. (limit = CMD_DEMOCHAT platform_id is_finish_select CMD_USER_DATA_

OFFSET=0xb68f2c TERM=Turn
CONTEXT=hCommandDequeueHzRateRecentBasicStatisticsMaxSize DequeueHzAccelerationMarginBufferSize MatchControlAlgorithm MinKeepBufferSize CorrectionFallDeterminationNotReadyForCommandDeltaCount AsymmetricInputDelayTurnLimitEnable AsymmetricInputDelayTurnSuddenChangeEnable EnableManufactureModelNamePresetType Dscp ScrambleEnable TcpFallbackEnable DcTestQuickModeNumTest ObserveRecordTimeoutMs DisableBufferingControlInSetPlay ImportantKickCommandMustEnable MultiplaySessionRecvSub Refresh retry limit exceeded. (limit = CMD_DEMOCHAT platform_id is_finish_select CMD_USER_DATA_SYNC CHANGED_ADDRESS UHP_KEEPALIVE h

OFFSET=0xb6941c TERM=Turn
CONTEXT=Item getIntroductoryPricePeriod (Lcom/android/billingclient/api/PurchaseHistoryRecord;)Ljava/lang/String; (Lcom/android/billingclient/api/BillingResult;Lcom/android/billingclient/api/BillingConfig;)V android_product_id bundled_items CmdSendTurnAddressData CmdWatchNotice MultiplayPrivilegeCheckTask WIRED M3 statistics save_interval_msec jp/konami/android/common/GetRooting grpc.http2.max_ping_strikes grpc.initial_reconnect_backoff_ms grpc.per_rpc_retry_buffer_size handshaker round_robin g_core_codegen_interface->grpc_call_start_batch( call_.call(), nullptr, 0, core_cq_tag(), nullptr) == GRPC_CALL_OK

OFFSET=0xb7bf1e TERM=Turn
CONTEXT=oftedPass ApiManager PlatformAuthTaskImpl CongestionControlWindowSizeRecentBasicStatisticsMaxSize KeepBufferSize BufferSizeRawSmoothCoefficient CorrectionRiseDeterminationTimeMsThresholdHigh CorrectionFallThresholdHigh EnableSocketErrorLog TurnBufferCriticalConditionTimeMsMax DcTestUdpStickyAddressLongTimeoutMs DcTestForClientServerModeIntervalMs DcTestWebSocketClientDisableVerifyPeer P2P_ADHOC_WIFIDIRECTLAN_HIGH_LEVEL FastTcpSrttSmoothCoefficient ChannelSendQueueBufferLength MultiplaySessionRecv DONE_ONE_PUNCHING %d:%d; SOURCE_ADDRESS ALTERNATE_SERVER RP_HOST_ADDRESS USER_ID O573_CR_RESP RP_EXIT 

OFFSET=0xb8f0ed TERM=Turn
CONTEXT= tag_joinRoom TaskLobbyRoomGuest preset_quick m_myCondition TaskSyncTeamSelect TaskMultiplayIndicator CMD_GET_BIG_DATA CMD_SEND_CAMPAIGN_PASS_NEXT_STAGE invitedPlayGoIgnoreAlertActivity POINT Match/End/MatchEnd %02x%02x_%ld %s_f04 MarseilleTurn Heading .00 G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineSystem\Api\OnlineSystemApiManagerVer2.cpp PlatformAuthTask m_userName m_stadiumName dec1 (event|data|id|retry): ?(.+) Xrq-RtAF_91MAE82 (Landroid/content/Context;Ljava/lang/String;ZLjava/lang/String;[BZZ)I RxPpsRecentBasicStatisticsMaxSize MatchCommandBufferingControl PredictKeepBufferS

OFFSET=0xb8f2d7 TERM=Turn
CONTEXT=String;ZLjava/lang/String;[BZZ)I RxPpsRecentBasicStatisticsMaxSize MatchCommandBufferingControl PredictKeepBufferSizeDeltaFromMatchStopCountEnable CorrectionFall CorrectionFallThresholdLow AsymmetricInputDelayWifiEnable AsymmetricInputDelayTurnEnable UERenderThreadAffinityMask samsung/SCV49|samsung/SC-42A TurnNetworkIoEwmaSmoothCoef WebSocketClientEnableIgnoreUnknownCa NetworkTesterSlowPingIntervalMs PingIntervalUs LinkTimeoutUs KeepAliveTimerUs MinCongestionWindowSize ScalableTcpBeta DefaultRto SlowdownDetectionInFastForwardMarginHz MatchAbortTimerCoefficient LoadTimeoutMs Sub Allocate retry limi

OFFSET=0xb8f31a TERM=Turn
CONTEXT=MatchCommandBufferingControl PredictKeepBufferSizeDeltaFromMatchStopCountEnable CorrectionFall CorrectionFallThresholdLow AsymmetricInputDelayWifiEnable AsymmetricInputDelayTurnEnable UERenderThreadAffinityMask samsung/SCV49|samsung/SC-42A TurnNetworkIoEwmaSmoothCoef WebSocketClientEnableIgnoreUnknownCa NetworkTesterSlowPingIntervalMs PingIntervalUs LinkTimeoutUs KeepAliveTimerUs MinCongestionWindowSize ScalableTcpBeta DefaultRto SlowdownDetectionInFastForwardMarginHz MatchAbortTimerCoefficient LoadTimeoutMs Sub Allocate retry limit exceeded. (limit = MAPPED_ADDRESS O573_REV urn:schemas-upnp-org:

OFFSET=0xba2dc9 TERM=Turn
CONTEXT=hCoefficient MediaSpecificDecoderMaxBufferLength MatchCommandHzLowLimitCoefficient Change state. ( G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineSystem\Multiplay\SessionStrategy\OnlineSystemMultiplaySessionStrategyP2pFullMeshTurnOnly.cpp G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineSystem\Multiplay\SessionStrategy\Session\OnlineSystemObserveSession.cpp CMD_ALLREADY_FLAG guest_num canUseWiFi :: XOR_PEER_ADDRESS Skip Attr >> [ %s ] WANPPPConnection SCPDURL {"device":{ NewNATEnabled AddPortMapping {"igd":{"status":"%s","lastError":"%s","uptime":"%d","rsip":"%d","nat":"%

OFFSET=0xbaf2cd TERM=Turn
CONTEXT=ediaEvent__DelegateSignature SupportsRate MTOF_Default TransformOriginActor Binding bShowBurnin AspectRatioAxisConstraint CaptureGamut bCompressed bUseCompression OnBeginCursorOver FEdGraphSchemaAction LODMethod OnTakeAnyDamage DefaultPawn_TurnRate ForwardY EventWait/WorldTickMisc Tonemapper DirectionalLights VectorFields SelectionOutline VolumetricLightmap LargeVertices Splines Atmosphere Rendering VisualizeVolumetricLightmap VisualizeShadingModels TimerManager UEngine::InitializeObjectReferences DisableInput K2_AddActorWorldTransformKeepScale InParent CinematicTextureGroups bVal bNetUseOwnerRele

OFFSET=0xbb6437 TERM=Turn
CONTEXT=eMainMenuInfoWork Common/CmnReset AgeGateEnd TaskLoginSubCreateUser Error CMD_GET_GAME_SESSION local_limited custom_league TaskOnlineAdDownloader CustomStadiumList0.bin TaskSeasonMainMenuCheckBeforeMatch SendJoinUserCompeRequest %s_f02 ChopTurn mx DlToMemApi } https?\://([^/]+)[/$]?([^/]+)?[/$]? sign= httpObjNull NetworkQualityTestForP2pFullMesh CS_HIGH_LEVEL ActualMatchHzRecentBasicStatisticsMaxSize DequeueHzRate DequeueHzAccelerationMarginCoefficient CorrectionRiseDeterminationNotReadyForCommandDeltaCount CorrectionFallDeterminationNotReadyForCommandDeltaCountThresholdHigh UERenderThreadPriorit

OFFSET=0xbb8aa3 TERM=Turn
CONTEXT=ch_start_window ProcessMatchSetup level_select time_attack_proceed CEMBLEM EURO SU_12 SA_C_NMB_E30 SA_C_NMB_E34 SA_C_NMB54 SA_C_NMB58 SA_C_NMB96 CheckOneCallFlag CheckProcessingSide CheckNumInTimeZoneBackupEvent CheckFoulJudgementKind CheckTurnEndRecordVariousData CheckLastLinePosition CheckConditionForCheckSdConfig CheckCompeStageForCup EnterDemoType LeagueRankVariousData WinPointVariousData SequenceEvent EFLeagueData LOST_BALL RUN KNOCKOUT_ROUND_RANK3 KNOCKOUT_ROUND_RANK5 FREE_CHANCE_AREA OBJECTION SCENE_ANTHEMAFTER B1 CUP_SAME CUP_INTER CUP_LIB LG_SPA2 NUM_ATTACK NUM_FREEND_PA NUM_DIFF_ENEMY_PA

OFFSET=0xbbe173 TERM=Turn
CONTEXT=GetOverallCaptureKindVariationIndex HomeNameTextureActorPtr PlayTranslationAnimation MaxMax actionData_Key SetUniformClothWeight SetUniformConfigFrontNumber isHighcut m_refereee_prop_compos MenuWindowPadEventDecide SetCursorOutCheckColor isTurnBack SetRecord TeamSideType ECustomStadiumParamType::KickoffEffect ParamType EDataStoreValueType::Bool deactivateOther EDemoPropInfoFlag::Logo2White EDemoHomeAway Role bSet DemoEngineSubsystemIntChangedSignature__DelegateSignature DemoEngineSubsystem GetInt SetScrollListScrollOffset isCall ELatestFadeLayerEnum EFadeWipeKindEnum::FADE_WIPE_KIND_WIPE ParentCom

OFFSET=0xbbe9ea TERM=Turn
CONTEXT=nalNormalSectionVertexIndexMap EyePositionRight EStateEnum::STATE_DESTROY InColorAndOpacity bSimpleTextMode OnReachedNextIndex_AutoScroll__DelegateSignature idx AutoScrollAnimType CursorData ScrollLeft m_parentWidget m_cursorDataMap_Key SetTurnBack SetCloseBtn TouchableWidgetTouchDelegate__DelegateSignature ENotTouchHitReason::TileViewSwipeMoving ETouchableType::Normal InAnimation bForceDebugDrawTouchPoint ChoiceDownAnimationName OnChangedScrollIndex CachedChoiceInactiveAnim EMyClubCmnNarrowDownCenterViewCheckMark::CHECK_MARK_RIGHT_ADD_EMBLEM EMenuAlertBoxTypeAM::ALERT_BOX_1_1 EMenuAlertBoxTypeCS 

OFFSET=0xbc995b TERM=Turn
CONTEXT=vel CgkI2KWEy_UIEAIQTQ TaskLobbyJoinRoom Intro/ProcessIntroSystemDataLoad TaskWatchGameResult CMD_GET_MAINMENU_MATCH_PRESET_INFO CMD_UNSUBSCRIBE_GRPC TaskSettingsSupportPersonalize %ld_ %ld_l 0000_b07_%d_ %s_f05_lim %s_m01_%ld_max CutBehindTurn GKLongThrows AcrobaticClearance 12 cn G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineSystem\Auth\OnlineSystemAuthUserIdStorage.cpp JSON_PARSE_ERROR ExecuteFindClass MatchesManager , Own = CS P2P_GIVE_UP_QUICKLY_LEVEL MatchCommandLatencyRecentBasicStatisticsMaxSize AsymmetricInputDelayThreshold AppYieldIdleThreadIntervalMs CmpNetworkIoVersion 

OFFSET=0xbc9add TERM=Turn
CONTEXT=cpp JSON_PARSE_ERROR ExecuteFindClass MatchesManager , Own = CS P2P_GIVE_UP_QUICKLY_LEVEL MatchCommandLatencyRecentBasicStatisticsMaxSize AsymmetricInputDelayThreshold AppYieldIdleThreadIntervalMs CmpNetworkIoVersion NameResolverTimeoutMs TurnNetworkIoQuickPingIntervalMs DcTestEraseUdpStickyFailure DcTestVersion AccessLineTesterMaxTtl P2P_ADHOC_BLE_GIVE_UP_QUICKLY_LEVEL FastTcpAlpha FastTcpGamma ChannelSchedulerPriority Update connection ID. ( Responded stun method. (ALLOCATE_ERROR_RESPONSE) ACTIVENETWORK:CELLULAR RETRY_PUNCHING ::%s0 BINDING RP_ENTRY MappingTestIG ${"%s":"[ %s ][ %s ] from [ %s 

OFFSET=0xbef2e2 TERM=Turn
CONTEXT=asicStatisticsMaxSize InputDelayBufferSizeCorrectionRecentBasicStatisticsMaxSize InputDelayInMatchCommandActiveRecentBasicStatisticsMaxSize CorrectionFallDeterminationTimeMs CorrectionFallDeterminationTimeMsThresholdLow AsymmetricInputDelayTurnDelayDisconnect AppYieldCpuOnlineRateThreshold MultiplaySessionDaemonStatisticsIoBufferEnable ObservePlaybackBufferLength TimeWaitTimeoutMs P2P_ADHOC_WIFIDIRECTLAN P2P_ADHOC_BTC_GIVE_UP_QUICKLY_LEVEL P2P_ADHOC_BLE DelayBasedLimiterHeavyCongestionFactor SlowdownDetectionInFastForwardEnable MatchCommandBufferingControlType InitializationTimeoutMs Closed. (Conn

OFFSET=0xbefc3f TERM=Turn
CONTEXT= Tools\OnlineSystem\GetServerKeyword\GetServerKeyword.exe getPackageName isAutoRenewing nativeKonamiIabInitializationFinished buyItem (Ljava/lang/String;ILjava/lang/String;Ljava/lang/String;)I CmdGetTurnServerList.php MOBILE_DUN DWN TUNNEL grpc.http2.hpack_table_size.encoder grpc.http2.bdp_probe grpc.experimental.tcp_read_chunk_size inproc connectivity_state executor G:/PES22HC/Dev-600Series/Source/Shared/basic/ext/grpc/grpc/include/grpcpp/impl/codegen/client_interceptor.h false && "It is illegal to call FailHijackedRecvMessage on a " "method which has a Ca

OFFSET=0xbf1cb8 TERM=Turn
CONTEXT=="%s" <![CDATA[%s]]> version="%s" A1_TGC FrontWaitTime DoubleSpeed Not CheckTempValueForConfigMessageBoard CheckPowewfulTeam CheckUniformNumber CheckRestartKindHistry CheckOwnGoal CheckPenaltyAreaPlayerNum CheckSituationNoPassTarget CheckTurnEndKind CheckPlayerInSector CheckMoveDistFromPassEvent CheckChanceLevelInfo CheckConditionPlayerVoiceSdConfig FormationRole InterceptAreaStats CursorInfoVariousData OneCallKind PlayerIdType VariableRoleData RANK2_GOAL MEMBER_ANNOUNCEMENT GOAL_AREA KNOCKOUT_ROUND_FIRST KNOCKOUT_ROUND_TO_QFINAL EDIT_OK WEAK BOOS_FOUL SPEC ENTER_BGM_IS_ANTHEM RANGE_NATIONAL_H 1

OFFSET=0xc02447 TERM=Turn
CONTEXT=UserCompeGetUserCompeInfo TaskSetUserName DIVISION Captaincy 23 ERR_CANCELED %06d send callback failed Def_Online_gRPC_insecure : { GetRequestReceiveTime P2P_ADHOC_UNKNOWN_LOW_LEVEL BufferWarningLv2ConditionBufferSizeThreshold ScrambleCode TurnNetworkIoDegradedByLatencyEnable ConnectMainWaitTimeMS DcTestRecvTimeoutMs NetworkQualityIndicatorUpdateIntervalMs WebSocketClientDisableVerifyPeer NetworkTesterBaseRttMeasurementTimeMs RttSummaryStatisticsWindowSize ProtocolChannel Responded stun method. (CHANNEL_BIND_SUCCESS_RESPONSE) The username and/or password are not set. guest_list getCurrentNetworkIn

OFFSET=0xc15a99 TERM=Turn
CONTEXT=PlaybackMatchActiveStatusCheckTimeMs DefaultPps FecQueueMediaSpecificEnable MatchRecvCallRecvPossibleEnable is_finish chatNo CMD_PLATFORM_SESSION REQUEST_PUNCHING RecvStunMsg FF0E::C NewEnabled GetExternalIPAddress {"mappingList":{ ## AllocTurnPort Endpoint NotFound. ## MISC ${"Seed":%02x%02x%02x%02x%02x%02x} ${"Abort":%08x} ALLOC_PERM E_ADD_PORT_MAPPING_ERROR START_UDP_HOLE_PUNCHING_ERROR KEEPALIVE PEER_HOST pes_thread_onsys_manager total_timeout IOS android ps5 XBX onmode NATTYPE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L3_MCACTIVE MATCH_STOP_MAX_ROLLING_COUNT_BUF_EMPTY_IV3_MCACTIVE AT_OFFENCE_BACKGR

OFFSET=0xc17b63 TERM=Turn
CONTEXT=A_C_NMB95 sq_list.xml <! encoding SP_P%06d_%04dA A1_V2 A1_T0 A1_T0A SA_V2 A1_P0 CheckNowHalf CheckAddedTimeVariousData CheckIsForfeitedGame CheckSideBallTouchRecord CheckActAreaBackupEvent CheckDiffLineFriendTopEnemyLast CheckFreePlayerLastTurnover CheckOffenceRecordVariousData CheckPassSituationOffenceRecord CheckAreaFromWideLine CheckConditionForDribbleSdConfig ActingShootFailedLevel OffenceRecordVariousData ConceptKind TeamStyle ChallengeMatchData OUTBALL FOLLOW FOLLOW_DF TOP_SPEED STADIUM_SELECT A1 OH OFFENCE_ENEMY GK_THROW CUP_ENG_SP LG_ITA LG_ENG LG_JPN1 INT_PRE_ASIA INT_PRE_CNT_PO THROUGHPA

OFFSET=0x1b67cc TERM=turn
CONTEXT=5physx2Sc18ParticleSystemCore16setInternalFlagsENS_7PxFlagsINS_18PxParticleBaseFlag4EnumEtEE _ZN5physx2Sc18ParticleSystemCore17notifyCpuFallbackEv _ZN5physx2Sc18ParticleSystemCore20obtainStandaloneDataEv _ZN5physx2Sc18ParticleSystemCore20returnStandaloneDataEPNS_2Pt12ParticleDataE _ZN5physx2Sc18ParticleSystemCoreC2ERKNS_11PxActorType4EnumEjb _ZN5physx2Sc18ParticleSystemCoreD2Ev _ZN5physx6shdfnd8FPUGuardC1Ev _ZN5physx6shdfnd8FPUGuardD1Ev _ZNK5physx2Sc17ParticleSystemSim18getSimParticleDataERNS_2Pt25ParticleSystemSimDataDescEb _ZNK5physx2Sc18ParticleSystemCore14getParticleMapEv _ZNK5physx2Sc18Partic

OFFSET=0x27c53f TERM=turn
CONTEXT=ataBuilder20suppressContractionsERKNS_10UnicodeSetER10UErrorCode _ZN6icu_6420CollationDataBuilder28copyContractionsFromBaseCE32ERNS_13UnicodeStringEijPNS_15ConditionalCE32ER10UErrorCode _ZN6icu_6420CollationDataBuilder28setPrimaryRangeAndReturnNextEiijiR10UErrorCode _ZN6icu_6420CollationDataBuilder3addERKNS_13UnicodeStringES3_PKliR10UErrorCode _ZN6icu_6420CollationDataBuilder5addCEElR10UErrorCode _ZN6icu_6420CollationDataBuilder5buildERNS_13CollationDataER10UErrorCode _ZN6icu_6420CollationDataBuilder6getCEsERKNS_13UnicodeStringEPli _ZN6icu_6420CollationDataBuilder6getCEsERKNS_13UnicodeStringES3_Pl

OFFSET=0x2a8c2f TERM=turn
CONTEXT=t_tPj _ZNK3AAT10StateTableINS_13ObsoleteTypesEvE8sanitizeEP21hb_sanitize_context_tPj _ZNK3AAT11FeatureName18get_selector_infosEjPjP37hb_aat_layout_feature_selector_info_tS1_PKv _ZNK3AAT12KerxSubTable8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK3AAT12KerxSubTable8dispatchINS_22hb_aat_apply_context_tEEENT_8return_tEPS3_ _ZNK3AAT13ChainSubtableINS_13ExtendedTypesEE8dispatchI21hb_sanitize_context_tEENT_8return_tEPS5_ _ZNK3AAT13ChainSubtableINS_13ExtendedTypesEE8dispatchINS_22hb_aat_apply_context_tEEENT_8return_tEPS5_ _ZNK3AAT13ChainSubtableINS_13ExtendedTypesEE8sanitizeEP21hb_sanitize_cont

OFFSET=0x2a8c7f TERM=turn
CONTEXT=_tPj _ZNK3AAT11FeatureName18get_selector_infosEjPjP37hb_aat_layout_feature_selector_info_tS1_PKv _ZNK3AAT12KerxSubTable8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK3AAT12KerxSubTable8dispatchINS_22hb_aat_apply_context_tEEENT_8return_tEPS3_ _ZNK3AAT13ChainSubtableINS_13ExtendedTypesEE8dispatchI21hb_sanitize_context_tEENT_8return_tEPS5_ _ZNK3AAT13ChainSubtableINS_13ExtendedTypesEE8dispatchINS_22hb_aat_apply_context_tEEENT_8return_tEPS5_ _ZNK3AAT13ChainSubtableINS_13ExtendedTypesEE8sanitizeEP21hb_sanitize_context_t _ZNK3AAT13ChainSubtableINS_13ObsoleteTypesEE8dispatchI21hb_sanitize_contex

OFFSET=0x2a8ce0 TERM=turn
CONTEXT=_ZNK3AAT12KerxSubTable8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK3AAT12KerxSubTable8dispatchINS_22hb_aat_apply_context_tEEENT_8return_tEPS3_ _ZNK3AAT13ChainSubtableINS_13ExtendedTypesEE8dispatchI21hb_sanitize_context_tEENT_8return_tEPS5_ _ZNK3AAT13ChainSubtableINS_13ExtendedTypesEE8dispatchINS_22hb_aat_apply_context_tEEENT_8return_tEPS5_ _ZNK3AAT13ChainSubtableINS_13ExtendedTypesEE8sanitizeEP21hb_sanitize_context_t _ZNK3AAT13ChainSubtableINS_13ObsoleteTypesEE8dispatchI21hb_sanitize_context_tEENT_8return_tEPS5_ _ZNK3AAT13ChainSubtableINS_13ObsoleteTypesEE8dispatchINS_22hb_aat_apply_co

OFFSET=0x2a8d46 TERM=turn
CONTEXT=atchINS_22hb_aat_apply_context_tEEENT_8return_tEPS3_ _ZNK3AAT13ChainSubtableINS_13ExtendedTypesEE8dispatchI21hb_sanitize_context_tEENT_8return_tEPS5_ _ZNK3AAT13ChainSubtableINS_13ExtendedTypesEE8dispatchINS_22hb_aat_apply_context_tEEENT_8return_tEPS5_ _ZNK3AAT13ChainSubtableINS_13ExtendedTypesEE8sanitizeEP21hb_sanitize_context_t _ZNK3AAT13ChainSubtableINS_13ObsoleteTypesEE8dispatchI21hb_sanitize_context_tEENT_8return_tEPS5_ _ZNK3AAT13ChainSubtableINS_13ObsoleteTypesEE8dispatchINS_22hb_aat_apply_context_tEEENT_8return_tEPS5_ _ZNK3AAT13ChainSubtableINS_13ObsoleteTypesEE8sanitizeEP21hb_sanitize_conte

OFFSET=0x2a8df6 TERM=turn
CONTEXT=_13ExtendedTypesEE8dispatchINS_22hb_aat_apply_context_tEEENT_8return_tEPS5_ _ZNK3AAT13ChainSubtableINS_13ExtendedTypesEE8sanitizeEP21hb_sanitize_context_t _ZNK3AAT13ChainSubtableINS_13ObsoleteTypesEE8dispatchI21hb_sanitize_context_tEENT_8return_tEPS5_ _ZNK3AAT13ChainSubtableINS_13ObsoleteTypesEE8dispatchINS_22hb_aat_apply_context_tEEENT_8return_tEPS5_ _ZNK3AAT13ChainSubtableINS_13ObsoleteTypesEE8sanitizeEP21hb_sanitize_context_t _ZNK3AAT16LigatureSubtableINS_13ExtendedTypesEE5applyEPNS_22hb_aat_apply_context_tE _ZNK3AAT16LigatureSubtableINS_13ExtendedTypesEE8sanitizeEP21hb_sanitize_context_t _ZNK3

OFFSET=0x2a8e5c TERM=turn
CONTEXT=_13ExtendedTypesEE8sanitizeEP21hb_sanitize_context_t _ZNK3AAT13ChainSubtableINS_13ObsoleteTypesEE8dispatchI21hb_sanitize_context_tEENT_8return_tEPS5_ _ZNK3AAT13ChainSubtableINS_13ObsoleteTypesEE8dispatchINS_22hb_aat_apply_context_tEEENT_8return_tEPS5_ _ZNK3AAT13ChainSubtableINS_13ObsoleteTypesEE8sanitizeEP21hb_sanitize_context_t _ZNK3AAT16LigatureSubtableINS_13ExtendedTypesEE5applyEPNS_22hb_aat_apply_context_tE _ZNK3AAT16LigatureSubtableINS_13ExtendedTypesEE8sanitizeEP21hb_sanitize_context_t _ZNK3AAT18ContextualSubtableINS_13ExtendedTypesEE8sanitizeEP21hb_sanitize_context_t _ZNK3AAT18LookupSegment

OFFSET=0x2af32e TERM=turn
CONTEXT=_R8hb_set_t _ZN29hb_collect_features_context_t7visitedIN2OT7LangSysEEEbRKT_R8hb_set_t _ZN2OT11SubstLookup18apply_recurse_funcEPNS_21hb_ot_apply_context_tEj _ZN2OT11SubstLookup21dispatch_recurse_funcINS_27hb_collect_glyphs_context_tEEENT_8return_tEPS3_j _ZN2OT11SubstLookup29dispatch_closure_recurse_funcEPNS_20hb_closure_context_tEj _ZN2OT20hb_closure_context_t14is_lookup_doneEj _ZN2OT20hb_closure_context_t19should_visit_lookupEj _ZN2OT21hb_ot_apply_context_t19skipping_iterator_t4prevEv _ZN2OT26hb_get_subtables_context_t8apply_toINS_14ContextFormat1EEEbPKvPNS_21hb_ot_apply_context_tE _ZN2OT26hb_get_

OFFSET=0x2b020f TERM=turn
CONTEXT= _ZNK2OT10IndexArray14add_indexes_toEP8hb_set_t _ZNK2OT11RangeRecord12add_coverageI24hb_set_digest_combiner_tI27hb_set_digest_lowest_bits_tImLj4EES2_IS3_ImLj0EES3_ImLj9EEEEEEbPT_ _ZNK2OT11SingleSubst8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT11SingleSubst8dispatchINS_24hb_would_apply_context_tEEENT_8return_tEPS3_ _ZNK2OT11SingleSubst8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_ _ZNK2OT11SubstLookup7closureEPNS_20hb_closure_context_tEj _ZNK2OT11ValueFormat11apply_valueEPNS_21hb_ot_apply_context_tEPKvPKNS_7IntTypeItLj2EEER19hb_glyph_position_t _ZNK2OT11ValueFormat22s

OFFSET=0x2b025f TERM=turn
CONTEXT=geI24hb_set_digest_combiner_tI27hb_set_digest_lowest_bits_tImLj4EES2_IS3_ImLj0EES3_ImLj9EEEEEEbPT_ _ZNK2OT11SingleSubst8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT11SingleSubst8dispatchINS_24hb_would_apply_context_tEEENT_8return_tEPS3_ _ZNK2OT11SingleSubst8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_ _ZNK2OT11SubstLookup7closureEPNS_20hb_closure_context_tEj _ZNK2OT11ValueFormat11apply_valueEPNS_21hb_ot_apply_context_tEPKvPKNS_7IntTypeItLj2EEER19hb_glyph_position_t _ZNK2OT11ValueFormat22sanitize_value_devicesEP21hb_sanitize_context_tPKvPKNS_7IntTypeItLj2EEE _ZNK2OT12

OFFSET=0x2b02b1 TERM=turn
CONTEXT=_ImLj9EEEEEEbPT_ _ZNK2OT11SingleSubst8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT11SingleSubst8dispatchINS_24hb_would_apply_context_tEEENT_8return_tEPS3_ _ZNK2OT11SingleSubst8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_ _ZNK2OT11SubstLookup7closureEPNS_20hb_closure_context_tEj _ZNK2OT11ValueFormat11apply_valueEPNS_21hb_ot_apply_context_tEPKvPKNS_7IntTypeItLj2EEER19hb_glyph_position_t _ZNK2OT11ValueFormat22sanitize_value_devicesEP21hb_sanitize_context_tPKvPKNS_7IntTypeItLj2EEE _ZNK2OT12AlternateSet14collect_glyphsEPNS_27hb_collect_glyphs_context_tE _ZNK2OT12Alternate

OFFSET=0x2b04bb TERM=turn
CONTEXT=AlternateSet14collect_glyphsEPNS_27hb_collect_glyphs_context_tE _ZNK2OT12AlternateSet5applyEPNS_21hb_ot_apply_context_tE _ZNK2OT12AnchorMatrix8sanitizeEP21hb_sanitize_context_tj _ZNK2OT12ChainContext8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT12ChainContext8dispatchINS_21hb_ot_apply_context_tEEENT_8return_tEPS3_ _ZNK2OT12ChainContext8dispatchINS_24hb_would_apply_context_tEEENT_8return_tEPS3_ _ZNK2OT12ChainContext8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_ _ZNK2OT12ChainRuleSet11would_applyEPNS_24hb_would_apply_context_tERNS_30ChainContextApplyLookupContextE _ZNK2O

OFFSET=0x2b0509 TERM=turn
CONTEXT=nateSet5applyEPNS_21hb_ot_apply_context_tE _ZNK2OT12AnchorMatrix8sanitizeEP21hb_sanitize_context_tj _ZNK2OT12ChainContext8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT12ChainContext8dispatchINS_21hb_ot_apply_context_tEEENT_8return_tEPS3_ _ZNK2OT12ChainContext8dispatchINS_24hb_would_apply_context_tEEENT_8return_tEPS3_ _ZNK2OT12ChainContext8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_ _ZNK2OT12ChainRuleSet11would_applyEPNS_24hb_would_apply_context_tERNS_30ChainContextApplyLookupContextE _ZNK2OT12ChainRuleSet5applyEPNS_21hb_ot_apply_context_tERNS_30ChainContextApplyLooku

OFFSET=0x2b055a TERM=turn
CONTEXT=anitize_context_tj _ZNK2OT12ChainContext8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT12ChainContext8dispatchINS_21hb_ot_apply_context_tEEENT_8return_tEPS3_ _ZNK2OT12ChainContext8dispatchINS_24hb_would_apply_context_tEEENT_8return_tEPS3_ _ZNK2OT12ChainContext8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_ _ZNK2OT12ChainRuleSet11would_applyEPNS_24hb_would_apply_context_tERNS_30ChainContextApplyLookupContextE _ZNK2OT12ChainRuleSet5applyEPNS_21hb_ot_apply_context_tERNS_30ChainContextApplyLookupContextE _ZNK2OT12ConditionSet8evaluateEPKij _ZNK2OT12KernSubTableINS_20KernOTSu

OFFSET=0x2b05ad TERM=turn
CONTEXT=rn_tEPS3_ _ZNK2OT12ChainContext8dispatchINS_21hb_ot_apply_context_tEEENT_8return_tEPS3_ _ZNK2OT12ChainContext8dispatchINS_24hb_would_apply_context_tEEENT_8return_tEPS3_ _ZNK2OT12ChainContext8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_ _ZNK2OT12ChainRuleSet11would_applyEPNS_24hb_would_apply_context_tERNS_30ChainContextApplyLookupContextE _ZNK2OT12ChainRuleSet5applyEPNS_21hb_ot_apply_context_tERNS_30ChainContextApplyLookupContextE _ZNK2OT12ConditionSet8evaluateEPKij _ZNK2OT12KernSubTableINS_20KernOTSubTableHeaderEE8dispatchIN3AAT22hb_aat_apply_context_tEEENT_8return_tEPS6_ _ZNK2OT12

OFFSET=0x2b0704 TERM=turn
CONTEXT=okupContextE _ZNK2OT12ChainRuleSet5applyEPNS_21hb_ot_apply_context_tERNS_30ChainContextApplyLookupContextE _ZNK2OT12ConditionSet8evaluateEPKij _ZNK2OT12KernSubTableINS_20KernOTSubTableHeaderEE8dispatchIN3AAT22hb_aat_apply_context_tEEENT_8return_tEPS6_ _ZNK2OT12KernSubTableINS_20KernOTSubTableHeaderEE8sanitizeEP21hb_sanitize_context_t _ZNK2OT12KernSubTableINS_21KernAATSubTableHeaderEE8dispatchI21hb_sanitize_context_tEENT_8return_tEPS5_ _ZNK2OT12KernSubTableINS_21KernAATSubTableHeaderEE8dispatchIN3AAT22hb_aat_apply_context_tEEENT_8return_tEPS6_ _ZNK2OT13AnchorFormat210get_anchorEPNS_21hb_ot_apply_co

OFFSET=0x2b07bf TERM=turn
CONTEXT=derEE8dispatchIN3AAT22hb_aat_apply_context_tEEENT_8return_tEPS6_ _ZNK2OT12KernSubTableINS_20KernOTSubTableHeaderEE8sanitizeEP21hb_sanitize_context_t _ZNK2OT12KernSubTableINS_21KernAATSubTableHeaderEE8dispatchI21hb_sanitize_context_tEENT_8return_tEPS5_ _ZNK2OT12KernSubTableINS_21KernAATSubTableHeaderEE8dispatchIN3AAT22hb_aat_apply_context_tEEENT_8return_tEPS6_ _ZNK2OT13AnchorFormat210get_anchorEPNS_21hb_ot_apply_context_tEjPfS3_ _ZNK2OT13AnchorFormat310get_anchorEPNS_21hb_ot_apply_context_tEjPfS3_ _ZNK2OT13HintingDevice11get_x_deltaEP9hb_font_t _ZNK2OT13HintingDevice11get_y_deltaEP9hb_font_t _ZNK2O

OFFSET=0x2b082d TERM=turn
CONTEXT=erEE8sanitizeEP21hb_sanitize_context_t _ZNK2OT12KernSubTableINS_21KernAATSubTableHeaderEE8dispatchI21hb_sanitize_context_tEENT_8return_tEPS5_ _ZNK2OT12KernSubTableINS_21KernAATSubTableHeaderEE8dispatchIN3AAT22hb_aat_apply_context_tEEENT_8return_tEPS6_ _ZNK2OT13AnchorFormat210get_anchorEPNS_21hb_ot_apply_context_tEjPfS3_ _ZNK2OT13AnchorFormat310get_anchorEPNS_21hb_ot_apply_context_tEjPfS3_ _ZNK2OT13HintingDevice11get_x_deltaEP9hb_font_t _ZNK2OT13HintingDevice11get_y_deltaEP9hb_font_t _ZNK2OT13LigatureSubst8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT13MultipleSubst8dispatchI21hb_sani

OFFSET=0x2b0964 TERM=turn
CONTEXT=t_tEjPfS3_ _ZNK2OT13AnchorFormat310get_anchorEPNS_21hb_ot_apply_context_tEjPfS3_ _ZNK2OT13HintingDevice11get_x_deltaEP9hb_font_t _ZNK2OT13HintingDevice11get_y_deltaEP9hb_font_t _ZNK2OT13LigatureSubst8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT13MultipleSubst8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT14AlternateSubst8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT14ContextFormat111would_applyEPNS_24hb_would_apply_context_tE _ZNK2OT14ContextFormat114collect_glyphsEPNS_27hb_collect_glyphs_context_tE _ZNK2OT14ContextFormat15applyEPNS_21hb_ot_apply_context_t

OFFSET=0x2b09af TERM=turn
CONTEXT=PfS3_ _ZNK2OT13HintingDevice11get_x_deltaEP9hb_font_t _ZNK2OT13HintingDevice11get_y_deltaEP9hb_font_t _ZNK2OT13LigatureSubst8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT13MultipleSubst8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT14AlternateSubst8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT14ContextFormat111would_applyEPNS_24hb_would_apply_context_tE _ZNK2OT14ContextFormat114collect_glyphsEPNS_27hb_collect_glyphs_context_tE _ZNK2OT14ContextFormat15applyEPNS_21hb_ot_apply_context_tE _ZNK2OT14ContextFormat17closureEPNS_20hb_closure_context_tE _ZNK2OT14Cont

OFFSET=0x2b09fb TERM=turn
CONTEXT=11get_y_deltaEP9hb_font_t _ZNK2OT13LigatureSubst8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT13MultipleSubst8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT14AlternateSubst8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT14ContextFormat111would_applyEPNS_24hb_would_apply_context_tE _ZNK2OT14ContextFormat114collect_glyphsEPNS_27hb_collect_glyphs_context_tE _ZNK2OT14ContextFormat15applyEPNS_21hb_ot_apply_context_tE _ZNK2OT14ContextFormat17closureEPNS_20hb_closure_context_tE _ZNK2OT14ContextFormat211would_applyEPNS_24hb_would_apply_context_tE _ZNK2OT14ContextForm

OFFSET=0x2b0fc5 TERM=turn
CONTEXT=sDefFormat116intersects_classEPK8hb_set_tj _ZNK2OT15ClassDefFormat216intersects_classEPK8hb_set_tj _ZNK2OT15CoverageFormat112add_coverageI8hb_set_tEEbPT_ _ZNK2OT16ExtensionFormat1INS_12ExtensionPosEE8dispatchI21hb_sanitize_context_tEENT_8return_tEPS5_ _ZNK2OT16ExtensionFormat1INS_14ExtensionSubstEE8dispatchI21hb_sanitize_context_tEENT_8return_tEPS5_ _ZNK2OT16SinglePosFormat114collect_glyphsEPNS_27hb_collect_glyphs_context_tE _ZNK2OT16SinglePosFormat18sanitizeEP21hb_sanitize_context_t _ZNK2OT16SinglePosFormat214collect_glyphsEPNS_27hb_collect_glyphs_context_tE _ZNK2OT16SinglePosFormat25applyEPNS_21

OFFSET=0x2b1029 TERM=turn
CONTEXT=ZNK2OT15CoverageFormat112add_coverageI8hb_set_tEEbPT_ _ZNK2OT16ExtensionFormat1INS_12ExtensionPosEE8dispatchI21hb_sanitize_context_tEENT_8return_tEPS5_ _ZNK2OT16ExtensionFormat1INS_14ExtensionSubstEE8dispatchI21hb_sanitize_context_tEENT_8return_tEPS5_ _ZNK2OT16SinglePosFormat114collect_glyphsEPNS_27hb_collect_glyphs_context_tE _ZNK2OT16SinglePosFormat18sanitizeEP21hb_sanitize_context_t _ZNK2OT16SinglePosFormat214collect_glyphsEPNS_27hb_collect_glyphs_context_tE _ZNK2OT16SinglePosFormat25applyEPNS_21hb_ot_apply_context_tE _ZNK2OT16SinglePosFormat28sanitizeEP21hb_sanitize_context_t _ZNK2OT17CaretVal

OFFSET=0x2b13e1 TERM=turn
CONTEXT=_t _ZNK2OT17FeatureVariations15find_substituteEjj _ZNK2OT17MarkLigPosFormat15applyEPNS_21hb_ot_apply_context_tE _ZNK2OT17MarkLigPosFormat18sanitizeEP21hb_sanitize_context_t _ZNK2OT17PosLookupSubTable8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_j _ZNK2OT17PosLookupSubTable8dispatchINS_21hb_ot_apply_context_tEEENT_8return_tEPS3_j _ZNK2OT17PosLookupSubTable8dispatchINS_25hb_add_coverage_context_tI24hb_set_digest_combiner_tI27hb_set_digest_lowest_bits_tImLj4EES3_IS4_ImLj0EES4_ImLj9EEEEEEEENT_8return_tEPSB_j _ZNK2OT17PosLookupSubTable8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_j

OFFSET=0x2b1435 TERM=turn
CONTEXT=NS_21hb_ot_apply_context_tE _ZNK2OT17MarkLigPosFormat18sanitizeEP21hb_sanitize_context_t _ZNK2OT17PosLookupSubTable8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_j _ZNK2OT17PosLookupSubTable8dispatchINS_21hb_ot_apply_context_tEEENT_8return_tEPS3_j _ZNK2OT17PosLookupSubTable8dispatchINS_25hb_add_coverage_context_tI24hb_set_digest_combiner_tI27hb_set_digest_lowest_bits_tImLj4EES3_IS4_ImLj0EES4_ImLj9EEEEEEEENT_8return_tEPSB_j _ZNK2OT17PosLookupSubTable8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_j _ZNK2OT17PosLookupSubTable8dispatchINS_27hb_collect_glyphs_context_tEEENT_8return_t

OFFSET=0x2b14e8 TERM=turn
CONTEXT=osLookupSubTable8dispatchINS_21hb_ot_apply_context_tEEENT_8return_tEPS3_j _ZNK2OT17PosLookupSubTable8dispatchINS_25hb_add_coverage_context_tI24hb_set_digest_combiner_tI27hb_set_digest_lowest_bits_tImLj4EES3_IS4_ImLj0EES4_ImLj9EEEEEEEENT_8return_tEPSB_j _ZNK2OT17PosLookupSubTable8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_j _ZNK2OT17PosLookupSubTable8dispatchINS_27hb_collect_glyphs_context_tEEENT_8return_tEPS3_j _ZNK2OT17hb_kern_machine_tIN3AAT19KerxSubTableFormat0INS_20KernOTSubTableHeaderEE13accelerator_tEE4kernEP9hb_font_tP11hb_buffer_tjb _ZNK2OT17hb_kern_machine_tIN3AAT19KerxSu

OFFSET=0x2b1541 TERM=turn
CONTEXT=kupSubTable8dispatchINS_25hb_add_coverage_context_tI24hb_set_digest_combiner_tI27hb_set_digest_lowest_bits_tImLj4EES3_IS4_ImLj0EES4_ImLj9EEEEEEEENT_8return_tEPSB_j _ZNK2OT17PosLookupSubTable8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_j _ZNK2OT17PosLookupSubTable8dispatchINS_27hb_collect_glyphs_context_tEEENT_8return_tEPS3_j _ZNK2OT17hb_kern_machine_tIN3AAT19KerxSubTableFormat0INS_20KernOTSubTableHeaderEE13accelerator_tEE4kernEP9hb_font_tP11hb_buffer_tjb _ZNK2OT17hb_kern_machine_tIN3AAT19KerxSubTableFormat0INS_21KernAATSubTableHeaderEE13accelerator_tEE4kernEP9hb_font_tP11hb_buffer_

OFFSET=0x2b159b TERM=turn
CONTEXT=gest_lowest_bits_tImLj4EES3_IS4_ImLj0EES4_ImLj9EEEEEEEENT_8return_tEPSB_j _ZNK2OT17PosLookupSubTable8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_j _ZNK2OT17PosLookupSubTable8dispatchINS_27hb_collect_glyphs_context_tEEENT_8return_tEPS3_j _ZNK2OT17hb_kern_machine_tIN3AAT19KerxSubTableFormat0INS_20KernOTSubTableHeaderEE13accelerator_tEE4kernEP9hb_font_tP11hb_buffer_tjb _ZNK2OT17hb_kern_machine_tIN3AAT19KerxSubTableFormat0INS_21KernAATSubTableHeaderEE13accelerator_tEE4kernEP9hb_font_tP11hb_buffer_tjb _ZNK2OT17hb_kern_machine_tIN3AAT19KerxSubTableFormat2INS_20KernOTSubTableHeaderEE13acc

OFFSET=0x2b1e04 TERM=turn
CONTEXT=Format35applyEPNS_21hb_ot_apply_context_tE _ZNK2OT19ChainContextFormat37closureEPNS_20hb_closure_context_tE _ZNK2OT19ChainContextFormat38sanitizeEP21hb_sanitize_context_t _ZNK2OT19SubstLookupSubTable8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_20hb_closure_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_21hb_ot_apply_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_24hb_would_apply_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_25hb_add_coverage_context_tI24hb_set_digest_combin

OFFSET=0x2b1e59 TERM=turn
CONTEXT=0hb_closure_context_tE _ZNK2OT19ChainContextFormat38sanitizeEP21hb_sanitize_context_t _ZNK2OT19SubstLookupSubTable8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_20hb_closure_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_21hb_ot_apply_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_24hb_would_apply_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_25hb_add_coverage_context_tI24hb_set_digest_combiner_tI27hb_set_digest_lowest_bits_tImLj4EES3_IS4_ImLj0EES4_ImLj9EEEEEEEENT_8return_tEP

OFFSET=0x2b1eaf TERM=turn
CONTEXT=_ZNK2OT19SubstLookupSubTable8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_20hb_closure_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_21hb_ot_apply_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_24hb_would_apply_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_25hb_add_coverage_context_tI24hb_set_digest_combiner_tI27hb_set_digest_lowest_bits_tImLj4EES3_IS4_ImLj0EES4_ImLj9EEEEEEEENT_8return_tEPSB_j _ZNK2OT19SubstLookupSubTable8dispatchINS_26hb_get_subtables_context_tEEENT_8retur

OFFSET=0x2b1f08 TERM=turn
CONTEXT=19SubstLookupSubTable8dispatchINS_20hb_closure_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_21hb_ot_apply_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_24hb_would_apply_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_25hb_add_coverage_context_tI24hb_set_digest_combiner_tI27hb_set_digest_lowest_bits_tImLj4EES3_IS4_ImLj0EES4_ImLj9EEEEEEEENT_8return_tEPSB_j _ZNK2OT19SubstLookupSubTable8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_27hb_collect_glyphs_context_tEEENT_8re

OFFSET=0x2b1fbd TERM=turn
CONTEXT=kupSubTable8dispatchINS_24hb_would_apply_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_25hb_add_coverage_context_tI24hb_set_digest_combiner_tI27hb_set_digest_lowest_bits_tImLj4EES3_IS4_ImLj0EES4_ImLj9EEEEEEEENT_8return_tEPSB_j _ZNK2OT19SubstLookupSubTable8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_27hb_collect_glyphs_context_tEEENT_8return_tEPS3_j _ZNK2OT20LigatureSubstFormat111would_applyEPNS_24hb_would_apply_context_tE _ZNK2OT20LigatureSubstFormat114collect_glyphsEPNS_27hb_collect_glyphs_context_tE _ZNK2OT20Lig

OFFSET=0x2b2018 TERM=turn
CONTEXT=pSubTable8dispatchINS_25hb_add_coverage_context_tI24hb_set_digest_combiner_tI27hb_set_digest_lowest_bits_tImLj4EES3_IS4_ImLj0EES4_ImLj9EEEEEEEENT_8return_tEPSB_j _ZNK2OT19SubstLookupSubTable8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_27hb_collect_glyphs_context_tEEENT_8return_tEPS3_j _ZNK2OT20LigatureSubstFormat111would_applyEPNS_24hb_would_apply_context_tE _ZNK2OT20LigatureSubstFormat114collect_glyphsEPNS_27hb_collect_glyphs_context_tE _ZNK2OT20LigatureSubstFormat15applyEPNS_21hb_ot_apply_context_tE _ZNK2OT20LigatureSubstFormat17closureE

OFFSET=0x2b2074 TERM=turn
CONTEXT=_lowest_bits_tImLj4EES3_IS4_ImLj0EES4_ImLj9EEEEEEEENT_8return_tEPSB_j _ZNK2OT19SubstLookupSubTable8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_j _ZNK2OT19SubstLookupSubTable8dispatchINS_27hb_collect_glyphs_context_tEEENT_8return_tEPS3_j _ZNK2OT20LigatureSubstFormat111would_applyEPNS_24hb_would_apply_context_tE _ZNK2OT20LigatureSubstFormat114collect_glyphsEPNS_27hb_collect_glyphs_context_tE _ZNK2OT20LigatureSubstFormat15applyEPNS_21hb_ot_apply_context_tE _ZNK2OT20LigatureSubstFormat17closureEPNS_20hb_closure_context_tE _ZNK2OT20MultipleSubstFormat114collect_glyphsEPNS_27hb_collect_g

OFFSET=0x2b2b77 TERM=turn
CONTEXT=fINS_6RecordINS_7FeatureEEENS_7IntTypeItLj2EEEE8sanitizeEP21hb_sanitize_context_tPKv _ZNK2OT7ArrayOfINS_6RecordINS_7LangSysEEENS_7IntTypeItLj2EEEE8sanitizeEP21hb_sanitize_context_tPKv _ZNK2OT7Context8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT7Context8dispatchINS_24hb_would_apply_context_tEEENT_8return_tEPS3_ _ZNK2OT7Context8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_ _ZNK2OT7Feature8sanitizeEP21hb_sanitize_context_tPKNS_25Record_sanitize_closure_tE _ZNK2OT7PairPos8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_ _ZNK2OT7PairSet14collect_glyphsEPNS_27hb

OFFSET=0x2b2bc2 TERM=turn
CONTEXT=text_tPKv _ZNK2OT7ArrayOfINS_6RecordINS_7LangSysEEENS_7IntTypeItLj2EEEE8sanitizeEP21hb_sanitize_context_tPKv _ZNK2OT7Context8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT7Context8dispatchINS_24hb_would_apply_context_tEEENT_8return_tEPS3_ _ZNK2OT7Context8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_ _ZNK2OT7Feature8sanitizeEP21hb_sanitize_context_tPKNS_25Record_sanitize_closure_tE _ZNK2OT7PairPos8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_ _ZNK2OT7PairSet14collect_glyphsEPNS_27hb_collect_glyphs_context_tEPKNS_11ValueFormatE _ZNK2OT7PairSet5applyEPNS_21h

OFFSET=0x2b2c0f TERM=turn
CONTEXT=izeEP21hb_sanitize_context_tPKv _ZNK2OT7Context8dispatchI21hb_sanitize_context_tEENT_8return_tEPS3_ _ZNK2OT7Context8dispatchINS_24hb_would_apply_context_tEEENT_8return_tEPS3_ _ZNK2OT7Context8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_ _ZNK2OT7Feature8sanitizeEP21hb_sanitize_context_tPKNS_25Record_sanitize_closure_tE _ZNK2OT7PairPos8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_ _ZNK2OT7PairSet14collect_glyphsEPNS_27hb_collect_glyphs_context_tEPKNS_11ValueFormatE _ZNK2OT7PairSet5applyEPNS_21hb_ot_apply_context_tEPKNS_11ValueFormatEj _ZNK2OT7PairSet8sanitizeEP21hb_sani

OFFSET=0x2b2caf TERM=turn
CONTEXT=8return_tEPS3_ _ZNK2OT7Context8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_ _ZNK2OT7Feature8sanitizeEP21hb_sanitize_context_tPKNS_25Record_sanitize_closure_tE _ZNK2OT7PairPos8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_ _ZNK2OT7PairSet14collect_glyphsEPNS_27hb_collect_glyphs_context_tEPKNS_11ValueFormatE _ZNK2OT7PairSet5applyEPNS_21hb_ot_apply_context_tEPKNS_11ValueFormatEj _ZNK2OT7PairSet8sanitizeEP21hb_sanitize_context_tPKNS0_18sanitize_closure_tE _ZNK2OT7RuleSet14collect_glyphsEPNS_27hb_collect_glyphs_context_tERNS_33ContextCollectGlyphsLookupContextE _ZNK2OT8Cla

OFFSET=0x2b412a TERM=turn
CONTEXT=t_tERNS_32ChainContextClosureLookupContextE _ZNK2OT9ChainRule8sanitizeEP21hb_sanitize_context_t _ZNK2OT9MarkArray5applyEPNS_21hb_ot_apply_context_tEjjRKNS_12AnchorMatrixEjj _ZNK2OT9SinglePos8dispatchINS_26hb_get_subtables_context_tEEENT_8return_tEPS3_ _ZNK3AAT19KerxSubTableFormat2IN2OT20KernOTSubTableHeaderEE11get_kerningEjjPNS_22hb_aat_apply_context_tE _ZNK3AAT19KerxSubTableFormat2IN2OT20KernOTSubTableHeaderEE8sanitizeEP21hb_sanitize_context_t _ZNK3AAT19KerxSubTableFormat2IN2OT21KernAATSubTableHeaderEE11get_kerningEjjPNS_22hb_aat_apply_context_tE _ZNK3AAT19KerxSubTableFormat2IN2OT21KernAATSubTabl

OFFSET=0x2d1cb2 TERM=turn
CONTEXT=ice_GetSpatializer criAsrVoice_GetTime criAsrVoice_IsDropped criAsrVoice_IsPlaying criAsrVoice_IsStop criAsrVoice_OutputToChStrip criAsrVoice_Pause criAsrVoice_PutPacket criAsrVoice_ResetDspParameters criAsrVoice_ResetRouting criAsrVoice_ReturnPacket criAsrVoice_SetCallback criAsrVoice_SetContext criAsrVoice_SetDspActiveSwitch criAsrVoice_SetDspParameter criAsrVoice_SetInputCallback criAsrVoice_SetInsertionDsp criAsrVoice_SetMatrix criAsrVoice_SetRendererType criAsrVoice_SetRouting criAsrVoice_SetSamplingRate criAsrVoice_SetSpatializer criAsrVoice_SetTimeOffset criAsrVoice_Setup criAsrVoice_Start 

OFFSET=0x2e41f5 TERM=turn
CONTEXT=emoveTask criFsDevice_RequestToResume criFsDevice_RequestToSuspend criFsDispatcher_AddItem criFsDispatcher_Create criFsDispatcher_Destroy criFsDispatcher_GetActionItem criFsDispatcher_GetItemNum criFsDispatcher_RemoveItem criFsDispatcher_ReturnActionItem criFsList_AddHead criFsList_AddTail criFsList_Create criFsList_Destroy criFsList_GetItemNum criFsList_GetTopPriorityItem criFsList_Remove criFsGroupLoader_GetBinderId criFsGroupLoader_GetNumLoadersPerGroupLoader criFsGroupLoader_IsPreparing criFsGroupLoader_LimitNumLoaders criFsLoader_SetIgnoreEofFlag criFsLoader_SetVerifyFlag g_grpldrsys criFsIo_

OFFSET=0x9ba25d TERM=turn
CONTEXT=xt_Event_Value_%d Title_Sort Card_Exist Text_Nomination_Value_3 GraphParts_You GaugeParts_4 AnalystUsageRateGauge Text_Common CmnPlayerPositionAreaSmall CmnPlayerPositionGetAreaSmall CallbackPopupAlertSetDefaultStadiumSelectCancel FrameInReturn Btn_Short CmnOrangeGuideToDown RecordRoom_Away Img_SeasonPoint CallbackHeaderTextAnimation Text_CircleGraph_Value CloseFilterView FameViewFooterJump OnClosedCampaignPassPointAlert EventEndAlertCallback CallbackAlert StartMatching DeclineCompe ScoreText_SF_%d SF_%d_%s TileViewCustom_QF_%d userId HOME[%d] AWAY[%d] Receive_First_Show A. R diger CQ_Immediate 

OFFSET=0x9bca09 TERM=turn
CONTEXT=CoopUserInfo::InGame ELayoutMatchMainMenuCoopUserRequest::Unselect ELayoutMatchRoomMainMenuLobbyUserInfo::Success RoomIdStr UserInfo BtnPtrAry ELayoutMatchRoomMainMenuEventCoopSelectParts::Do GetEventInfo IsFinishGetSelectedRoomInfo StartReturnFromMatch ELobbyRoomMatchSettingsItem::USER_COMMENT ResetMatchEnv m_ownerIndex count EMenuMailboxInfoGetType MenuMailboxNewsLinkInfo GetLastSceneNo m_overall bronzeSize EPauseCameraType::PAUSE_CAMERA_TYPE_1ON1_CUSTOM CanEnterHighlight IsBigMatch stadiumId EMatchSettingsRadarIconColor::MATCH_SETTING_RADAR_ICON_BLUE EMatchSettingsRadarIconColor m_defaultIconCo

OFFSET=0x9be42e TERM=turn
CONTEXT=ueueSubmit(Queue, 1, &SubmitInfo, Fence->GetHandle()) VulkanRHI::vkGetSwapchainImagesKHR(Device.GetInstanceHandle(), SwapChain, &NumSwapChainImages, nullptr) AudioThread Linear execContext_FailSilent execFalse COND_SimulatedOrPhysics EAppReturnType EUnit::Minutes PF_R16F_FILTER PF_ASTC_6x6 ESearchDir::Type PackageName bRecursivePaths bIncludeOnlyOnDiskAssets AutomationExecutionEntry Int32RangeBound AnyKey Backslash A_AccentGrave Gamepad_RightX Gamepad_LeftStick_Up OculusTouch_Right_Trigger_Click ValveIndex_Left_Grip_Axis ValveIndex_Right_Trackpad_Right 5 = ETouchIndex AndroidThunkJava_GetDeviceOri

OFFSET=0x9c1314 TERM=turn
CONTEXT=rget SetLinearVelocityDrive GetTargetLocationAndRotation GrabLocation ESettingsLockedAxis::Type ExtraFOV DistanceFromPlaneFadeoutStart DelegateArray TViewTarget ToAlpha bHoldWhenFinished bIsOrthographic ClientCancelPendingMapChange ClientReturnToMainMenu EnableCheats ServerUpdateLevelVisibility AnimToStop InputRollScale InputAxisProperties SetBind bLabelAssetsInMyDirectory ERendererStencilMask::ERSM_128 PrimitiveComponentInstanceData ClearMoveIgnoreComponents GetCollisionProfileName GetPhysicsAngularVelocity InBoxCentre bUseMaxLODAsImposter bReceiveMobileCSMShadows LpvBiasMultiplier bInitialVeloci

OFFSET=0x9c2fd4 TERM=turn
CONTEXT=ide_4_1 gkmovenear_HeisouSlant_3_0 gknearmovestep_fast_backslant_3_3 gkprejump_0_0_near_min_move defenseMove_01_circle_short_parallel_3_3_inversion_act071 gkprejump_4_0_rotateRun_090 gkseeoff_high_react_3_0_y11 autoMove_40_circle_short_run_turn_2_2 goalnet_release_0_3_090_slow head_y07_sidle_3_0_f180 head_y09_0_0_180_rear head_y09_3_0_000_shed head_y09_sidle_3_0_f270 Throwin_BallCatchToSetup_3_0_y5_f135 idle_0_3_run_045 tacklefoot_mid_0_0_000_act068 kickoff_kicker_stand_pass kick_long_0_0_infront_y0_135_late kick_long_3_0_instep_y0_045_gerrard kick_mid_3_0_inside_y0_045_rear kick_mid_3_0_inside_y0

OFFSET=0x9c511a TERM=turn
CONTEXT=ble_pk.bin cpk_dat/common/demo/fixdemo/table_seamlessGoal.bin SetQuat ChangeMember match_enable match_pause_replay MainOtherStep dialog flow::FlowTransition::MAIN_STEP_JSON_LOAD_WAIT Because of m_isResetRunning == true, ClearUnits() and return. zh_TW st005 ligue2 model/training_prop/t_panel_stand/t_panel_stand_01.fpk SE_ST_CHECKPOINT @---- cpk_dat/common/anime/AnimeTable/bin/FootData.bin [adjustSp] SpChange: %.2f(%.2f / %d) camera_person_move_side_1_0 demo_gutsR_1_0 demo_miss_angry_0_1_0 demo_injury_pain_falldown dm_oop_lineup_idle_0_1 dm_oop_hurryup_045_idle_0_2_runslant demo_coop_touchMid dem

OFFSET=0x9c53bf TERM=turn
CONTEXT=man_flagup_loop seamless_liftup_pass_catch_0_0_y5_v2 seamless_liftup_self_catch_0_0_y5 blockfront_0_0_y06 blockfront_2_0_y02 blockside_3_0_y00 blockside_3_0_y00_reaction blockside_3_0_y02 fall_upbody_0_0 stagger_lowbody_3_3_tackle_m4_r goalturn_allfours goalturn_pointing_2_4_left demo_move_0_1_135_step demo_gk_glad_7 demo_angry_hurry_16 demo_miss_0_1_droop_135_1 demo_miss_3_1_face_045 demo_miss_0_1_head_135 demo_miss_facedown demo_miss_faceup_1 demo_gk_miss_facedown_1 demo_droop_hurry_10 demo_appeal_hurry_13 demo_appeal_hurry_23 demo_appeal_hurry_24 dodge_human_slide_rapid_up_4_4 dodge_ball_0_0_cr

OFFSET=0x9c53d1 TERM=turn
CONTEXT=amless_liftup_pass_catch_0_0_y5_v2 seamless_liftup_self_catch_0_0_y5 blockfront_0_0_y06 blockfront_2_0_y02 blockside_3_0_y00 blockside_3_0_y00_reaction blockside_3_0_y02 fall_upbody_0_0 stagger_lowbody_3_3_tackle_m4_r goalturn_allfours goalturn_pointing_2_4_left demo_move_0_1_135_step demo_gk_glad_7 demo_angry_hurry_16 demo_miss_0_1_droop_135_1 demo_miss_3_1_face_045 demo_miss_0_1_head_135 demo_miss_facedown demo_miss_faceup_1 demo_gk_miss_facedown_1 demo_droop_hurry_10 demo_appeal_hurry_13 demo_appeal_hurry_23 demo_appeal_hurry_24 dodge_human_slide_rapid_up_4_4 dodge_ball_0_0_crouch dodge_ball_2_

OFFSET=0x9c8ad5 TERM=turn
CONTEXT=_get1_extensions_present tls13_final_finish_mac tls_construct_cke_gost tls_construct_stoc_cryptopro_bug bad ecc cert binder does not verify dane tlsa bad matching type dtls message too big no verify cookie callback old session cipher not returned sslv3 alert certificate unknown ssl session id has bad length tlsv1 unrecognized name unable to find public key parameters unsupported ssl version legacy_server_connect ciphersuites chainCAfile SSLv3/TLS read change cipher spec PINIT TRCV TED access denied rsa_pss_pss_sha256 rsa_pss_pss_sha512 CLIENT_HANDSHAKE_TRAFFIC_SECRET CLIENT_TRAFFIC_SECRET_0 StrmI

OFFSET=0x9c8ddc TERM=turn
CONTEXT=ySetStrikeArenaMulti Online/EvCompe/ProcEvCompeEventInit Online/EvCompe/MlEvent/ProcEvCompeEventEnter Online/StrikeArena/ProcStrikeArenaTutorial path_to_glory_ready tutorial_result attention_demo Online/Match/GroupPreMatchMenu group_disp return_group_league StrikeArenaMenu longBall CMD_TEAM_DATA_SYNC ExecuteConsoleCommand "r.CustomDepth 0" DebugMenu /tmp TEMBLEM CED BGM1_ORG_CMP%04d_CHAMP A1_BT0_03 DevelopData/soundScript/develop/Script/Xml_Mobile/Common/CrowdNoise/Tree/ SE_AMBIENT_NORM SE_A_AMBIENT_EXCITE SA_C_NMB_E09 SA_C_NMB_E11 SA_C_NMB_E41 SA_C_NMB_E45 SA_C_NMB_E82 SA_C_NMB91 SA_C_NMB94 SE_RO

OFFSET=0x9ccde6 TERM=turn
CONTEXT=rIcon.cpp MemberChange_2/Hide personarized AlertPartsText Icon_AuthenticTeam AlertPartsGroupBtn SetMaxCharNum CallbackClosedEntryAlert OnDestroyed /Game/Assets/ui/Data/Widget/Parts/Others/CmnLinkPitch/CmnLinkPitch_4.CmnLinkPitch_4_C Icon_ReturnList TeamHighlight_Off Text_Emblem void UMenuTaskUserActionFriendBase::CallbackClosedConfirmAlert() void UMenuTaskUserActionBase::SetBaseStep(const BaseStep) virtual bool UMenuTaskUserActionEditUserName::ActionCustom() Text_ActionInteractive OnCloseDetailCallBack SetAgeCategoryList BindDialogCallbackEvent void UPlayerCardFrontInfo::SetBooster(const bool, con

OFFSET=0x9d316d TERM=turn
CONTEXT=stancesEnded EAnimLinkMethod::Absolute EAnimLinkMethod::Type bEnableRootMotionTranslation EPinHidingMode::Type AnimNode_TransitionResult MeshComp Received_NotifyTick TrackNames LinkupCache ETransitionBlendMode EndNotify bDesiredTransitionReturnValue EComponentType::TranslationZ ECurveBlendOption::BlendByWeight AAT_LocalSpaceBase AssetManagerRedirect OnPrimaryAssetClassListLoaded__DelegateSignature AsyncLoadPrimaryAssetList NewLightColor bAtmosphereAffectsSunIlluminance bDisableGroundScattering BoolParam SourceBusSendLevel bAllowPlayWhenSilent ExteriorVolume SetSubmixSendSettings NewSubmixOverrideS

OFFSET=0x9d6ad0 TERM=turn
CONTEXT=id_3_0_inside_y0_045_punch gkdropball_0_3_fast block_0_0_y00_f090_veryfar dm_oop_gk_idle_0_0_idle_guts_06 autoMove_01_reverse_loop_parallel_side_3_3_STEP_mid autoMove_06_zigzag135_side_loop_2_2_STEP_mid autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_mid dm_oop_ballcome_handup_one_far_f090_walkslant_1_1_parallel_045 dm_oop_lineback_f090_mid_delay dm_oop_pass_point_f045_run_3_4_f045 autoMove_01_reverse_loop_parallel_back_2_2_mid_michael autoMove_01_reverse_loop_parallel_side_2_2_STEP_near autoMove_01_reverse_loop_slant_backslant_2_2_STEP_near autoMove_03_crank90_loop_1_1_mid_michael autoMove_08

OFFSET=0x9d73cf TERM=turn
CONTEXT=ew_dribblerun_preslowdown_3_3_f090_y0_out_ver20 enum_dummy112 enum_dummy113 LongVersion_171104_F111_t01_Gabriel_01 enum_dummy201 enum_dummy208 enum_dummy247 enum_dummy264 autoMove_02_gkmovenear_goto_reverse_stop02_1_1 enum_dummy283 dash_04_turn_4_4_150_act079 dash_06_back_2_4_run_270_act068 dash_06_slant_2_4_parallel_090_act068 dash_06_slant_2_4_run_f315_act068 dash_07_dash_4_2_side_near_ball_follow_act079 dm_oop_gk_idle_0_0_mortifying_000_v03 dm_oop_gk_sidestep_2_0_Glad_000_v02 dm_oop_angry_1_3_090_act071_03 dm_oop_angry_3_3_180_act064_02 dm_oop_droop_1_3_090_act064_02 dm_oop_praise_2_3_090_atf09

OFFSET=0x9d7f48 TERM=turn
CONTEXT=it_registry heightMax WindActionParam paramFloat BGM_ORG_GIMMICK_MATCH_01 DevelopData/common/match/constant/stadium/demoarea_st032.json DevelopData/common/match/constant/stadium/demoarea_st079.json B_LeftCam_spawn R_mic_2R MainRight repeat turnAngleNum ballAngleHStart ballSpeed nonSpinRate rollToSpeedSpeedYMin paramTable gk_entry baseRatingMedian subValue40percent goalKickBackSpin thinkDistMiddle floatValue04 pauseRestartMoveRot startBallPlayerNo p1_angle_rigth distForGageMin paraMaxSpeedRate targetDist powerfullShootGageMax40 targetDistSec animeCancelFrame Entrance adjustReturnDist baseMfTargetLi

OFFSET=0x9d809d TERM=turn
CONTEXT=gMedian subValue40percent goalKickBackSpin thinkDistMiddle floatValue04 pauseRestartMoveRot startBallPlayerNo p1_angle_rigth distForGageMin paraMaxSpeedRate targetDist powerfullShootGageMax40 targetDistSec animeCancelFrame Entrance adjustReturnDist baseMfTargetLineWidth checkAdjustDist diffRestartX_End limitBesideWidth maxWaitTime cpk_dat/common/demo/fixdemo/oop/table_oop.bin gani Instance001 match_path_to_glory_return FlowListener cpk_dat/common/script/flow/ Add stack : zh st007 cp_asia >>> match2dManagerSyncUe =player P

OFFSET=0x9d814f TERM=turn
CONTEXT=hootGageMax40 targetDistSec animeCancelFrame Entrance adjustReturnDist baseMfTargetLineWidth checkAdjustDist diffRestartX_End limitBesideWidth maxWaitTime cpk_dat/common/demo/fixdemo/oop/table_oop.bin gani Instance001 match_path_to_glory_return FlowListener cpk_dat/common/script/flow/ Add stack : zh st007 cp_asia >>> match2dManagerSyncUe =player Part= GOAL PLAYER cpk_dat/common/anime/Mbinfo/bin/PersonalizedData.bin ***** illegal Data!! CreateFOOTDATA() num:%d FOOTDATA_SIZE:%d size:%d [FaceHand] EyeBlink( false ) = %f [A

OFFSET=0x9d89c3 TERM=turn
CONTEXT=_y0_out trapchopside_l_0_4_y0_in_angle_ver2 trapfast_0_0_y4_far traplift_3_3_y2_boomerang traplift_0_0_y5 trapside_r_3_3_y5_out_near trapthrough_3_0_y6 kick_long_3_0_infront_y0_curve_drop_shoot demo_gk_glad_lie_14 head_3_0_y7_short_f springturn_0_3_l tapfake_0_3_r trapside_r_2_3_y0_in TO INJURY_LOOP [Contact] To Injury [dribble]dummy balldist=%f, hitdist=%f [feint_check]not isValid [GoalMove] Will Contact goal net [[TO_DEMO_MOVE]] footVR [Command] ControlMode [%s](fix or semiFix cursor & press point to play point dist(%.2f) is under 5M) G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Match

OFFSET=0x9e265e TERM=turn
CONTEXT=HOUSE OnFinishPaymentInfoAnimation EMenuMyClubNarrowDownFilterKind::EMENU_MYCLUB_NARROW_DOWN_FILTER_WAREHOUSE_PLAYER_LIST EMyClubPackAnnounceViewType::PURCHASED CallbackBackKeyPressed PickerDateDecideCallBackEvent__DelegateSignature eventReturnBirthday POTDPlayerCardBannerState ESeasonPointMenuChoiceKind::SEASON_POINT_MENU_CHOICE_NUM ECoinSelectResult::SuccessNormal EStarterSetType::StarterSet_C CallbackDecideChoice MenuWindowPtr OnUserActionFinishedEvents__DelegateSignature playMovieBtnStr OnAnnounceViewPackEndProceedBuyPack OnCloseConfiscatedCoinAlertPopup OnClosedReview EUserNameEditResult::Oth

OFFSET=0x9e330d TERM=turn
CONTEXT=ngState::WAIT_GET_ROOM_LIST EMainSelectAgingState::CREATE_ROOM SetMenuTrackrecordAcSearchroom WaitInitChoiceWidget roomNumber ELobbyRoomReqest::FadeFriendListInvitation ELobbyRoomReqest::FadeUserCompeInfo GetActionFooterNextAction IsAgingReturn IsEarnedBonusPoint StartSetRoomSettings ELayoutMatchMainMenuLobbyChoiceIcon::SquadManagement ELayoutMatchRoomMainMenuLobbyUserInfo::Waiting ELayoutMatchRoomMainMenuCoopIcon::Check UserRequestPtr SetMenuLobbyButtonTwo ELayoutMatchMainMenuEventCoop::MatchLevelInfo ELayoutMatchMainMenuEventCoopLobbyChoiceIcon::MatchHistory ELayoutMatchRoomMainMenuEventCoopSele

OFFSET=0x9e348a TERM=turn
CONTEXT=ing ELayoutMatchRoomMainMenuCoopIcon::Check UserRequestPtr SetMenuLobbyButtonTwo ELayoutMatchMainMenuEventCoop::MatchLevelInfo ELayoutMatchMainMenuEventCoopLobbyChoiceIcon::MatchHistory ELayoutMatchRoomMainMenuEventCoopSelectParts CheckedReturnedSquadDisable SetKicked infoList cmnRewardDispInfo MenuLoginBonusPresentInfo MenuLoginBonusPresentAgent ELoginBonusKind::LOGIN_BONUS_START_DASH EMenuMailboxReceiveResult::RECEIVE_RESULT_EPOINT_MAINTENANCE EMenuMailboxReceiveResult::RECEIVE_RESULT_UNKNOWN_ERROR GetEFootballPointValueStr isAscending TouchFooterSkip OnReleasedLCameraButton OnPressedFrameByFram

OFFSET=0x9e693f TERM=turn
CONTEXT=WhenPaused bOnlyCollidingComponents bSweep SweepHitResult NewRelativeRotation ReceiveTick bTearOff MinNetUpdateFrequency EAlphaBlendOption::CircularInOut bRecordTransforms AnimPlayRate AllowedTranslationFormats ACF_Fixed48NoW EMontagePlayReturnType GetInstanceAssetPlayerLength ResetDynamics bRespectMarkerOrder bStopAllMontages PrevSections AnimNode_Base FramesToCachePose Received_Notify AnimNotifyArray TotalDuration AnimSequenceTrackContainer PoseEvaluatorLinks BCS_BoneSpace EBoneAxis AssetImportInfo EPrimaryAssetCookRule::DevelopmentCook AssetScanPaths bApplyRecursively NewGroundScattering StartD

OFFSET=0x9e7eb4 TERM=turn
CONTEXT=nt JointIterations SolverPushOutIterations SetAngularSwing1Limit InForceLimit SetTargetLocation bSoftAngularConstraint bEnableEnhancedDeterminism SyncSceneSmoothingFactor PhysXTreeRebuildRate ThrustStrength PIDT_Custom AnimInstPool ClientReturnToMainMenuWithTextReason DeprojectScreenPositionToWorld GetFocalLocation GetInputVectorKeyState ForcedActor TravelType bIgnoreShift OnRep_UniqueId PoseContainer ERendererStencilMask::ERSM_4 EHasCustomNavigableGeometry::DontExport ECB_MAX SetGenerateOverlapEvents bShowTrace bPersistentShowTrace InputVector MassInKg DepthPriorityGroup AlwaysLoadOnServer MinFri

OFFSET=0x9ea115 TERM=turn
CONTEXT=row_0_0_045_fast block090_0_0_y00_180_far fall_upbody_2_0_020_tackle_lose_down_v3 feintrun_roulette_3_3_f045_y0_sole_sole_act064 feintrun_roulette_3_3_f067_y0_sole_sole_act064 head_y07_short_0_0_090_act064 autoMove_01_reverse_loop_parallel_turn_3_3_mid autoMove_08_ragged45_slant_loop_1_1_mid autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_face_only_mid dm_oop_lineup_f090_mid_delay_v3 autoMove_01_reverse_loop_front_back_2_2_STEP_near autoMove_01_reverse_loop_parallel_turn_2_2_near autoMove_05_zigzag135_front_loop_1_1_mid_michael coach_1_1_090_cross_arms autoMove_01_reverse_loop_slant_backslant_

OFFSET=0x9ea16f TERM=turn
CONTEXT=_roulette_3_3_f045_y0_sole_sole_act064 feintrun_roulette_3_3_f067_y0_sole_sole_act064 head_y07_short_0_0_090_act064 autoMove_01_reverse_loop_parallel_turn_3_3_mid autoMove_08_ragged45_slant_loop_1_1_mid autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_face_only_mid dm_oop_lineup_f090_mid_delay_v3 autoMove_01_reverse_loop_front_back_2_2_STEP_near autoMove_01_reverse_loop_parallel_turn_2_2_near autoMove_05_zigzag135_front_loop_1_1_mid_michael coach_1_1_090_cross_arms autoMove_01_reverse_loop_slant_backslant_2_2_STEP_near_gabriel gkgoalkick_Quick_short_0_0_f090_front ballTouch_03_3_dribble_player_

OFFSET=0x9ea200 TERM=turn
CONTEXT=llel_turn_3_3_mid autoMove_08_ragged45_slant_loop_1_1_mid autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_face_only_mid dm_oop_lineup_f090_mid_delay_v3 autoMove_01_reverse_loop_front_back_2_2_STEP_near autoMove_01_reverse_loop_parallel_turn_2_2_near autoMove_05_zigzag135_front_loop_1_1_mid_michael coach_1_1_090_cross_arms autoMove_01_reverse_loop_slant_backslant_2_2_STEP_near_gabriel gkgoalkick_Quick_short_0_0_f090_front ballTouch_03_3_dribble_player_wrap_around_2_2_045_and_090_y0_take1_gabriel dash_10_side_1_4_045_dash_Oriul new_dribble_0_4_f135_out ballTouch_05_5_dribble_touch_far_3_3_000_y0

OFFSET=0x9f039c TERM=turn
CONTEXT=] Dx recursive_mutex constructor failed %Lf random_device got EOF The expression contained an invalid escaped character, or a trailing escape. The expression contained an invalid character range, such as [b-a] in most encodings. carriage-return plus-sign right-brace xdigit Protracker Cloth not registered: returned NULL. G:\RenderPlat\Engine\Source\ThirdParty\PhysX3\PxShared\src\foundation\include/PsSortInternals.h PxConstraint %s not assigned to scene or assigned to another scene. Call will be ignored! static const char *physx::shdfnd::ReflectionAllocator<unsigned char *>::getName() [T = unsigned 

OFFSET=0x9f03e1 TERM=turn
CONTEXT= expression contained an invalid escaped character, or a trailing escape. The expression contained an invalid character range, such as [b-a] in most encodings. carriage-return plus-sign right-brace xdigit Protracker Cloth not registered: returned NULL. G:\RenderPlat\Engine\Source\ThirdParty\PhysX3\PxShared\src\foundation\include/PsSortInternals.h PxConstraint %s not assigned to scene or assigned to another scene. Call will be ignored! static const char *physx::shdfnd::ReflectionAllocator<unsigned char *>::getName() [T = unsigned char *] static const char *physx::shdfnd::ReflectionAllocator<physx::

OFFSET=0x9f1a4c TERM=turn
CONTEXT=E2016101201M:Failed to criCond_Create. E2019082000M E2013052701M E2010090802M E2020103000M:The linked library version is more recent than header version. Please update header. E2004090243 E2004090248 getUpper E2019100604:criServer Create return NULL. E2017060302 E2018041304M E2018041324M:vpx_codec_dec_init() error: 0x%08X CriUint32 E06100312 E08012805:Internal Error E08092651B E09021213:Failed in criCs_Create(). E2010041622 E2011120702:ACF file is not registered. E2012110806:The specified index is beyond the number of dsp setting snapshots. E2017080100:Invalid parameter format detected in Bandpass

OFFSET=0x9f294f TERM=turn
CONTEXT=aggedStorage LoadConsoleVariablesFromINI FEngineLoop::PreInitPostStartupScreen GEngine->Init WaitForMovieToFinish G:/UE4.26_eFB/Base/Engine/Source/Runtime/Engine/Classes/Curves/IndexedCurve.h EMediaCaptureCroppingType::Center StopCapture ReturnValue EMediaIOInputType::Fill MaxNeighborsPerCell Get Bool By ID Get Vector 4 By Index SampleSplinePositionByUnitDistanceWS GetSplineLocalToWorld MovieSceneNiagaraBoolParameterSectionTemplate ExplicitEmitter ExplicitSystem bSupportsGPU ID SetTickBehavior SetVariableInt ENCPoolMethod::ManualRelease NiagaraComponentPropertyBinding ManagedRenderTargets_Key Fill

OFFSET=0x9fdaea TERM=turn
CONTEXT=ichael autoMove_08_ragged45_slant_loop_3_3_STEP_mid_michael coach_1_1_090_cross_arms_calm_down head_y09_jostle_f_0_0_180_act095 autoMove_01_reverse_loop_front_back_2_2_STEP_near_gabriel autoMove_04_crank45_loop_3_3_near_gabriel autoMove_30_turn_move_3_3_CRANK_near_gabriel dash_10_walk_1_4_090_dash_Oriul gkmovemid_CatchMove_1_1_ball reaction_contact_2_3_135_act071_02 nearDribble_04_1_dribble_burst_2_4_000_y0_oriul nearDribble_04_1_dribble_burst_2_4_f180_y0_oriul new_dribblerun_arc_3m_3m_067_y0_in_act064 tacklefoot_sideways_mid_0_0_045_act100 reaction_overtaken_0_3_090_stagger_short_act064 dash_05_t

OFFSET=0x9fdc55 TERM=turn
CONTEXT=71_02 nearDribble_04_1_dribble_burst_2_4_000_y0_oriul nearDribble_04_1_dribble_burst_2_4_f180_y0_oriul new_dribblerun_arc_3m_3m_067_y0_in_act064 tacklefoot_sideways_mid_0_0_045_act100 reaction_overtaken_0_3_090_stagger_short_act064 dash_05_turn_4_3_180_CRANK js_back_1_1_loop_guard_back_main_halfturn dml_goal_celebrate_0121 gknearmovestep_fast_slant_0_3 gknearmovestep_run_step_1_3_3 dm_oop_pointing_f045_mid_delayback_2_2 dm_oop_pointing_f225_mid_delayside_1_1 dml_goal_celebrate_0191 dml_goal_celebrate_0269 enum_dummy14 F_ActualBattle_200127_F025_t01_Ortega_Fcut002 F_PES_20251203_K07_001_kubo_01_Fcu

OFFSET=0x9fdc8d TERM=turn
CONTEXT=arDribble_04_1_dribble_burst_2_4_f180_y0_oriul new_dribblerun_arc_3m_3m_067_y0_in_act064 tacklefoot_sideways_mid_0_0_045_act100 reaction_overtaken_0_3_090_stagger_short_act064 dash_05_turn_4_3_180_CRANK js_back_1_1_loop_guard_back_main_halfturn dml_goal_celebrate_0121 gknearmovestep_fast_slant_0_3 gknearmovestep_run_step_1_3_3 dm_oop_pointing_f045_mid_delayback_2_2 dm_oop_pointing_f225_mid_delayside_1_1 dml_goal_celebrate_0191 dml_goal_celebrate_0269 enum_dummy14 F_ActualBattle_200127_F025_t01_Ortega_Fcut002 F_PES_20251203_K07_001_kubo_01_Fcut001 enum_dummy19 new_dribblerun_2_3_135_axisback_in new

OFFSET=0x9fe1cb TERM=turn
CONTEXT=0 new_walkback_1_2_run_090_jump_relax new_walk_1_0_135 new_walk_1_1_225_relax enum_dummy148 LongVersion_171104_F114_t01_Gabriel_02 LongVersion_180928_F031_t01_Morgan_01 enum_dummy200 enum_dummy206 enum_dummy229 autoMove_40_circle_short_run_turn_2_2_bodyangle_keep_act079 dash_06_side_2_4_run_f090_act080 dash_06_slant_2_4_parallel_045_act068 dash_07_dash_4_1_side_near_ball_follow_act071 dash_07_dash_4_3_run_near_ball_follow_act071 dm_oop_gk_riseup_0_0_sideways_Glad_000 dm_oop_appeal_1_3_180_at045_act071 dm_oop_praise_1_3_000_at045_act071 enum_dummy309 enum_dummy362 enum_dummy367 LongVersion_201124_F

OFFSET=0xa01129 TERM=turn
CONTEXT=r)->last_err == UINT8_MAX connect() timed out grpc_event_engine_can_track_errors() anonymous_resource_user_%lx Disabling AF_INET6 sockets because socket() failed. listen failing recv_trailing_metadata_ready BIND_POLLSET key= query Server returned error recv_initial_metadata_ready Invalid incoming message compression algorithm: '%s'. Interpreting incoming data as uncompressed. grpc_channel_register_call(channel=%p, method=%s, host=%s, reserved=%p) G:\PES22HC\Dev-600Series\Source\Shared\basic\ext\grpc\grpc\src\core\lib\surface\server.cc slice_buffer->length <= UINT32_MAX RECV_INITIAL_METADATA ptr=%p

OFFSET=0xa02a4e TERM=turn
CONTEXT=hain tls_construct_ctos_server_name tls_construct_ctos_status_request tls_construct_finished tls_construct_stoc_next_proto_neg bad legacy version ca key too small dh key too small https proxy request no compression specified peer did not return a certificate pem name too short tlsv1 alert no renegotiation peer does not accept heartbeats unknown cmd name unsupported protocol no_tls1 +automatic SSLv3/TLS write hello request TLSv1.3 early data TWCKU handshake failure bad certificate status response extended master secret Exhibition/ExhibiPadConnection Match/Setup/MatchDirectSetup Online/EvCompe/Recor

OFFSET=0xa03547 TERM=turn
CONTEXT=he regular expression could match the specified character sequence. comma alpha static const char *physx::shdfnd::ReflectionAllocator<physx::Sq::PruningStructure>::getName() [T = physx::Sq::PruningStructure] Articulations not registered: returned NULL. Articulation initialization failed: returned NULL. PxArticulation NpSceneQueries.sceneQueriesDynamicPrunerUpdate PxScene::removeActor(): Individual articulation links can not be removed from the scene PxScene::addArticulation(): Articulation already assigned to a scene. Call will be ignored! PxScene::addArticulation(): Articulation link with zero ma

OFFSET=0xa0357a TERM=turn
CONTEXT=racter sequence. comma alpha static const char *physx::shdfnd::ReflectionAllocator<physx::Sq::PruningStructure>::getName() [T = physx::Sq::PruningStructure] Articulations not registered: returned NULL. Articulation initialization failed: returned NULL. PxArticulation NpSceneQueries.sceneQueriesDynamicPrunerUpdate PxScene::removeActor(): Individual articulation links can not be removed from the scene PxScene::addArticulation(): Articulation already assigned to a scene. Call will be ignored! PxScene::addArticulation(): Articulation link with zero mass added to scene; defaulting mass to 1 PxScene::se

OFFSET=0xa09660 TERM=turn
CONTEXT=eFilterKind::NO_FILTER IsReselectTeam EExchangeType::EEXCHANGE_ITEM typeList ClearIsTrainingFlowForward GetAlertCheckBoxText GetChangeNumMax IsDispAlertTutorial IsDispAutoPlaceIntroductionAlert IsEndCommandSquadMatchPlan IsErrorCommand IsReturnFromSubMenuFlow SwitchDispFormation UpdateDifferenceSqaudData order reserveOrderNo EGamePlanCustomCard EGamePlanMatchRoleSettingDispType::ROLE_SETTING_DISP_TYPE_PARTICIPANT_1 GetAutoSettingFeedBackStr EMenuGameSettingsSelect::MENU_GAME_SETTINGS_SELECT_SCREEN m_itemStr strHoaldingTimeBody EMenuLeagueMainMenuSubState::BEFORE_MATCH_CHECK_FAILED cmdErrorCode m_u

OFFSET=0xa09b67 TERM=turn
CONTEXT=OLLER ELobbySideSelectMenuState ELoginBonusKind::LOGIN_BONUS_KIND_NUM EMenuMailboxSortType::MAILBOX_SORT_PRIORITY EMenuMailboxInfoGetType::NUM presentList infoGetType ftitleStr fbodyStr DirectTouch OnReleasedFrameByFramePlusButton GetFlowReturnEvent m_hasLongThrow GetUniformNumberList EPauseCameraType::PAUSE_CAMERA_TYPE_MID_RANGE EPauseCameraType::PAUSE_CAMERA_TYPE_LONG m_cameraType Match2DLocalSkinType IsCustomStadium IsRainPossible EMenuMatchSettingsSubstitutionsCount::SUBSTITUTIONS_COUNT_3 EMenuMatchSettingsScreen::SCREEN_NAME_PLATE uniColor_r EMyClubChievementType::ACHIEVEMENT_TYPE_WEEKLY Upda

OFFSET=0xa0fb15 TERM=turn
CONTEXT=f045_lob kick_short_0_4_inside_y0_f045_r_045 kick_short_3_0_inside_y0_045 kick_short_3_0_inside_y0_090_side kick_short_3_0_outside_y6_f135 layer_direct_at_f090 lose_dribble_deprived_4_0_000 head_y09_shoot_0_0_090_act064 autoMove_30_dribble_turn_move_1_1_CRANK_mid_gabriel pk_runup_ronaldinho quick_restart90 referee_1_0_000_hand_middle_point_000 referee_game_end_1_0_hand_up_whistle referee_kickoff_start_0 js_run_3_2_000_guard_side_main_act095 js_dribbleslant_1_1_f045_out_guard_back_main_act064 feintrun_kick_4_3_000_y0_out_stepkick_act064 dribblerun_3_3_slide_090_in_ver7 gkblockcover_s01f04_3_0_y06_0

OFFSET=0xa1012f TERM=turn
CONTEXT=mid_y0_out_ver12 feintrun_roulette_2_3_f067_y0_sole_sole_act064 head_y07_short_0_0_180_act064 layer_gk_free_thrashHandNear dm_oop_gk_idle_0_0_idle_guts_07 autoMove_01_reverse_loop_slant_backslant_2_2_STEP_mid autoMove_01_reverse_loop_slant_turn_3_3_mid autoMove_04_crank45_loop_2_2_mid autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_mid coach_0_0_000_normal_oop_glad_high autoMove_30_turn_move_1_1_CRANK_mid dm_oop_calmdown_f045_idle autoMove_01_reverse_loop_front_back_1_1_mid_michael autoMove_01_reverse_loop_parallel_back_2_2_near autoMove_01_reverse_loop_parallel_back_3_3_mid_michael autoMove_0

OFFSET=0xa10182 TERM=turn
CONTEXT=180_act064 layer_gk_free_thrashHandNear dm_oop_gk_idle_0_0_idle_guts_07 autoMove_01_reverse_loop_slant_backslant_2_2_STEP_mid autoMove_01_reverse_loop_slant_turn_3_3_mid autoMove_04_crank45_loop_2_2_mid autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_mid coach_0_0_000_normal_oop_glad_high autoMove_30_turn_move_1_1_CRANK_mid dm_oop_calmdown_f045_idle autoMove_01_reverse_loop_front_back_1_1_mid_michael autoMove_01_reverse_loop_parallel_back_2_2_near autoMove_01_reverse_loop_parallel_back_3_3_mid_michael autoMove_01_reverse_loop_slant_backslant_1_1_mid_michael autoMove_03_crank90_loop_2_2_STEP_mi

OFFSET=0xa101c4 TERM=turn
CONTEXT=ts_07 autoMove_01_reverse_loop_slant_backslant_2_2_STEP_mid autoMove_01_reverse_loop_slant_turn_3_3_mid autoMove_04_crank45_loop_2_2_mid autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_mid coach_0_0_000_normal_oop_glad_high autoMove_30_turn_move_1_1_CRANK_mid dm_oop_calmdown_f045_idle autoMove_01_reverse_loop_front_back_1_1_mid_michael autoMove_01_reverse_loop_parallel_back_2_2_near autoMove_01_reverse_loop_parallel_back_3_3_mid_michael autoMove_01_reverse_loop_slant_backslant_1_1_mid_michael autoMove_03_crank90_loop_2_2_STEP_mid_michael head_y09_jostle_s_0_0_000_act064 autoMove_32_go_to_1_1_m

OFFSET=0xa10622 TERM=turn
CONTEXT=_01 nearDefense_04_BODYTURN_Slant_2_2_frontback_STEP_near_gabriel nearDribble_04_1_dribble_burst_2_4_f135_y0_oriul tacklefoot_parallel_near_0_0_000_act100 dribblerun_arc_3m_3m_067_y0_in_act064 dribblerun_arc_3m_3_f067_y0_out_act064 dash_05_turn_4_3_090_CRANK gkseeoff_side_react_3_0_y11 tackleshoulder_3_2_interrupt_blast_090_act102 dml_goal_celebrate_0059 dml_goal_celebrate_0066 dml_goal_celebrate_0089 dml_goal_celebrate_0100 dml_goal_celebrate_0271 D_PES_20251204_M01_002_nagao_14_Fcut001 dml_goal_celebrate_0274 StabilizerCam_runsideways_2_0_idle_L dm_oop_pass_point_f090_run_2_2_f090 dm_oop_pointin

OFFSET=0xa119b4 TERM=turn
CONTEXT=lk_1_1_side dm_miss_jog_2_1_walk_bendBack dm_miss_3_1_walk_repent demo_coop_instruct demo_pfm_cornerF_kick_r demo_pfm_starjump_0_0_l demo_goal_wide_sliding_loop throw_over_3_3_bothhard judge_whistle_0_0 linesman_stand_wait linesman_run_3_3_turn blockfront_2_0_y00_sliding fall_lowbody_0_0_l fall_lowbody_4_0_l stagger_lowbody_3_3_tackle_m0_r stagger_lowbody_3_3_tackle_m2_l stagger_upbody_3_3_v3 goalturn_hyper1_2_4 goalturn_guts2 demo_move_0_1_135_look demo_glad_0_0_000 demo_gk_glad_11 demo_gk_glad_lie_4 demo_angry_0_1_135_2 demo_miss_0_1_droop_090_2 demo_miss_0_2_droop_135_2 demo_miss_0_0_hip demo_m

OFFSET=0xa11a54 TERM=turn
CONTEXT= throw_over_3_3_bothhard judge_whistle_0_0 linesman_stand_wait linesman_run_3_3_turn blockfront_2_0_y00_sliding fall_lowbody_0_0_l fall_lowbody_4_0_l stagger_lowbody_3_3_tackle_m0_r stagger_lowbody_3_3_tackle_m2_l stagger_upbody_3_3_v3 goalturn_hyper1_2_4 goalturn_guts2 demo_move_0_1_135_look demo_glad_0_0_000 demo_gk_glad_11 demo_gk_glad_lie_4 demo_angry_0_1_135_2 demo_miss_0_1_droop_090_2 demo_miss_0_2_droop_135_2 demo_miss_0_0_hip demo_miss_1_1_back_droop demo_appeal_0_1_at045_5 demo_gk_cheer_4 TimeUp_1_0_Grad_2_0 HalfEnd_3_1_Normal_3 HalfEnd_3_1_Droop_0_0 dodge_human_jumplow_3 dodge_human_jump

OFFSET=0xa11a68 TERM=turn
CONTEXT=hard judge_whistle_0_0 linesman_stand_wait linesman_run_3_3_turn blockfront_2_0_y00_sliding fall_lowbody_0_0_l fall_lowbody_4_0_l stagger_lowbody_3_3_tackle_m0_r stagger_lowbody_3_3_tackle_m2_l stagger_upbody_3_3_v3 goalturn_hyper1_2_4 goalturn_guts2 demo_move_0_1_135_look demo_glad_0_0_000 demo_gk_glad_11 demo_gk_glad_lie_4 demo_angry_0_1_135_2 demo_miss_0_1_droop_090_2 demo_miss_0_2_droop_135_2 demo_miss_0_0_hip demo_miss_1_1_back_droop demo_appeal_0_1_at045_5 demo_gk_cheer_4 TimeUp_1_0_Grad_2_0 HalfEnd_3_1_Normal_3 HalfEnd_3_1_Droop_0_0 dodge_human_jumplow_3 dodge_human_jump_2 dodge_human_jumph

OFFSET=0xa15a35 TERM=turn
CONTEXT=ateParams.size() >= OldNumTemplateParamLists time_get_byname failed to construct for One of *?+{ was not preceded by a valid regular expression. Wrong version: PhysX version is 0x%08x, tried to create 0x%08x Cloth initialization failed: returned NULL. G:\RenderPlat\Engine\Source\ThirdParty\PhysX3\PhysX_3.4\Source\PhysX\src\NpArticulationLink.cpp G:\RenderPlat\Engine\Source\ThirdParty\PhysX3\PhysX_3.4\Source\compiler\cmake\android\..\..\..\PhysX\src/NpRigidActorTemplate.h PxScene::fetchResults: fetchResults() called illegally! It must be called after advance() or simulate() PxScene::shiftOrigin() 

OFFSET=0xa194a7 TERM=turn
CONTEXT=efault Choice_4 RewardRParts_2 uiEmblem_Home_White uiEmblem_White_5 Text_Advice Bar_First Receive_Before /Game/Assets/ui/Data/Widget/Match/Screen/MatchMenuTourPVPEvent/MatchMenuTourPVPEvent.MatchMenuTourPVPEvent_C Btn_On Text_TopicPath_2 return Plate_Offense /Game/Assets/menu/common/Views/WelcomeView/BP_MenuWelcomeView.BP_MenuWelcomeView_C /Game/Assets/menu/online/lobby/RoomSettingMatchSettings/BP_MenuLobbyRoomMatchSettingsSelectView.BP_MenuLobbyRoomMatchSettingsSelectView_C MatchMenuStrikeArenaPagePlayer CallbackAlertResendEmail Slider Plate_Default CommandClassic_Shoot_2 CommandClassic_Plate_Stu

OFFSET=0xa1a1c4 TERM=turn
CONTEXT=NextSequenceType::Button tileViewIndices InBallId Stain EBGIDEnum::BG_ID_PES SetBG ECharacterKind LoadCover SetUniformConfigShirtEmblem key backFont frontColor m_cloth_meshes_temp BlendFacialNoseR m_stainLimbMaskTex EventCursor PlayCursorReturn SetUiCheckMark ECommonWidgetLabelKind::FRAME_IN_PROCEED ECommonWidgetLabelKind::CURSOR_LEAVE PlacementType ECustomStadiumColorType::GoalnetColor1 ECustomStadiumParamType::Num PauseNotifications EnumValue BindingTable DemoCharacterRole TeamEmblemSubTexture EDemoCategory::CardPack EndDemoWinSideChanged ViewPlayerPoseNoChanged GetBackgroundSequence PushBool Se

OFFSET=0xa1a54d TERM=turn
CONTEXT=DirChanged AwayScore Away1st SetupLevel InMax EMatchFlowTask::WaitQuick EMatchFlowTask::Inplay EMatchFlowTask::PkMatchBeforeDemo EMatchFlowTask::SeamlessThrowin EMatchType::Normal SetWorkSelectTeamId EnumMap_Key Logger ready pChildWindow Return m_type ESupporterTeamType width CameraTableRow UniName dir HairAccessoryColor AssetDependencyDataInfo EPadDataNo::PAD_B EPadDataNo::PAD_CANCEL EDrawRatio::BP_DRAW_RATIO_NUM ETeamPowerStar::TEAM_POWER_STAR_3_5 EPlatformEnum::PLATFORM_ENUM_AM_HOS EWrokCategory::WORK_CATEGORY_MODE EUniformKindEnum::KIND_3RD EAgingState::UE_AGING_STATE_MATCH_STRIKE_ARENA_MULTI 

OFFSET=0xa21e83 TERM=turn
CONTEXT=0_0_y08 gkdeflect_s05_0_0_y04 gkcatch_f03_diveline_3_0_y00 gkmovemid_Stop_2_0_LongSlide gkmovenear_backslantstep_front_3_4_135 kick_long_0_0_y0_stagger_l_f045 kick_long_0_0_y0_stagger_l_f090_down gkmovenear_HeisouSide_3_3 gkmovenear_idlemidturn_090 gkmovenear_sidestep_0_4_1_short gkprejump_3_3_y05_rotateRun_M045_Otherside gkrise_faceupslow_0_0_f090 gkrise_faceup_0_3_000 gkrise_sidewaysslowknee_l_0_0_090 gkrise_sideways_l_0_0_000_hand gkrise_sideways_l_0_0_f090 gksavingCancel_s01_resign gksavingCancel_s03_short gkscoopout_lie_s03_0_0_y02_090_otherside gkseeoff_side_reactjump_0_0_y00 gknearmovestep_

OFFSET=0xa22768 TERM=turn
CONTEXT=_0_0_y06 slidingshort_parallel_3_0_f045_act064 trap_0_3_f090_y0_out_act097 traprun_3_3_s_f045_y0_in_ver21 feintrun_roulette_triple_lift_2_3_f270_y0_sole_sole_toe_ver23 js_run_2_0_000_tacklefoot_legscissors_down autoMove_40_circle_short_run_turn_3_3 autoMove_32_go_to_0_3m_near_act096 dm_oop_gk_cheer_riseup_sideways_appeal_0_0_045 dm_oop_gk_glad_riseup_facedown_dubbleguts_0_1_045 dm_oop_gk_lie_0_1_walkangry_f045 kick_long_3_0_inside_y0_045_curve_ronaldinho_2 js_idle_0_0_135_guard_side_set013_df_act068 block090_3_0_y04_000_far_L head_y09_sidle_3_1_000_clear autoMove_01_reverse_loop_front_back_3_3_mid

OFFSET=0xa2298b TERM=turn
CONTEXT=3_1_000_clear autoMove_01_reverse_loop_front_back_3_3_mid kick_mid_4_4_adjust_y0_000_sidle fall_upbody_2_0_020_tackle_lose_down_v2 js_run_4_4_000_guard_side_set017_pushed_of_act097 pk_runup_ronaldinho_2 autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_face_only_mid coach_0_0_000_normal_position_adjust dm_oop_ballcome_handup_one_far_f090_idle_0_1_side_090 dm_oop_linekeep_f135_mid_delay BallBoy_idle_crouch autoMove_01_dribble_reverse_loop_parallel_back_3_3_mid_gabriel autoMove_01_reverse_loop_parallel_side_3_3_STEP_mid_michael autoMove_01_reverse_loop_walkside_turn_1_1_mid_michael autoMove_03_cra

OFFSET=0xa22ad3 TERM=turn
CONTEXT=_one_far_f090_idle_0_1_side_090 dm_oop_linekeep_f135_mid_delay BallBoy_idle_crouch autoMove_01_dribble_reverse_loop_parallel_back_3_3_mid_gabriel autoMove_01_reverse_loop_parallel_side_3_3_STEP_mid_michael autoMove_01_reverse_loop_walkside_turn_1_1_mid_michael autoMove_03_crank90_loop_1_1_STEP_mid_michael autoMove_03_crank90_loop_3_3_mid_michael autoMove_05_zigzag135_front_loop_2_2_mid_michael autoMove_08_ragged45_slant_loop_3_3_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_STEP_mid_michael Freekick_stepback_0_2 coach_1_0_f090_cross_arms autoMove_32_go_to_2_2_mid_michael autoMove

OFFSET=0xa22bc5 TERM=turn
CONTEXT=rn_1_1_mid_michael autoMove_03_crank90_loop_1_1_STEP_mid_michael autoMove_03_crank90_loop_3_3_mid_michael autoMove_05_zigzag135_front_loop_2_2_mid_michael autoMove_08_ragged45_slant_loop_3_3_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_STEP_mid_michael Freekick_stepback_0_2 coach_1_0_f090_cross_arms autoMove_32_go_to_2_2_mid_michael autoMove_06_dribbel_zigzag135_side_loop_1_1_mid_gabriel autoMove_01_reverse_loop_parallel_back_3_3_near_gabriel autoMove_03_crank90_loop_2_2_STEP_near_gabriel autoMove_06_zigzag135_side_loop_2_2_STEP_near_gabriel dm_goal_extra_loop_0001 autoMove_00_b

OFFSET=0xa23edc TERM=turn
CONTEXT=atch/constant/positionPK/positionPK_5.json DevelopData/common/match/constant/stadium/demoarea_st028.json DevelopData/common/match/constant/stadium/demoarea_st043.json DevelopData/common/match/constant/stadium/demoarea_st050.json bench_home turnAngleAdd abilityExplosePowerNum ballAngleVAdd playerTrapPosY boundRate ballZRangeMarginUpper isLocalTransform coef_run gk_rate subValue20percent thinkDistFar gage floatValue05 playersAction startTutorialKind adjustAngle enemyDistMin angleMoveInputRange defaultBlendRate kickAddTime speed_0 offence TechnicalArea closePenetrateZRate closeRate_MF_adjustX dfAdjus

OFFSET=0xa24429 TERM=turn
CONTEXT=utsBanzai_1_0 dm_oop_pointing_045_idle_0_1_walkbackslant demo_pfm_jumpuppercut_3_3_l demo_goal_wide_sliding demo_goal_ivoryCoastDance_loop goalkick_instep_l puntkick_side_0_0_hard judge_advantage_1 seamless_catch_3_3_y2 seamless_carry_ball_turn_2_2 seamless_setplay_idle_ablique blockfront_0_0_y03_shoot_reaction_v2 fall_lowbody_2_0_v3_r stagger_upbody_2_2_hard_v2 demo_move_3_1_000 demo_move_0_1_135_face demo_move_tired_090 demo_glad_3_0_000_3 demo_gk_miss_fallside_4 demo_droop_hurry_12 demo_gk_appeal_2 demo_cheer_at000_3 demo_sorry_0_1_at135_1 demo_praise_hurry_12 demo_praise_hurry_19 kickfeint_dou

OFFSET=0xa26431 TERM=turn
CONTEXT=ION MATCH_COUNT BPS_RECEIVE_ UE_THREAD_ELAPSED_SINCE_LAST_UPDATED RECORED_TIME LAST_IPADDR DATA_TYPE RX_RLOSS_RATE_R_MAX Number of purchases: %d CmdGetProductList.php need_root_box_warn CmdGetSessionId str_list server_certificate retry_cmd_turn_address cpk_dat/common/etc/cacert.pem WIRELESS BT enable_indicator_stats_for_all getVersionName GetSOCManufacturer grpc.use_cronet_packet_coalescing grpc.grpclb_call_timeout_ms client_channel_routing orig_send_message_ != nullptr byte_count_ < total_size_ grpc_completion_queue_destroy(cq=%p) a->stolen_completion == nullptr completed_head.next == reinterpret

OFFSET=0xa2a8a3 TERM=turn
CONTEXT=[BI)V [ERROR] criVsd_M2tsSplitFinalizeReuseMemory called for using memory. Could not open the first m3u8 file(2). HTTP: %d, Code: %d, URL: "%s" E2021073001:Should initilize CRI Atom EX. [CRIVSD] Failed in gVdecApi->VideoDecodeRestart(), return 0x%08x allocate a frame buffer #%d done ... @0x%p E2019013149:Failed to configure/start MediaCodec. [CriVodStm] Failed to set an user agent used for downloading movie data. Current: [%u, %u], Downloaded: [%u, %u] E2022090509:Next sequence number is not found in current playlist. %s. (ILjava/lang/String;Ljava/lang/String;)V (I)Z vendorId productId WorldB

OFFSET=0xa351df TERM=turn
CONTEXT=097 gkdeflect_f05_3_0_y05_090 kick_long_0_0_adjust_y0_000 dm_oop_gk_riseup_sidewaysmid_l_0_2_000 blockhead_0_0_y05_f090_down blockhead_0_0_y06_f090_far_down dm_oop_gk_cheer_sidestep_clap_1_0_045 block_0_0_y01_000_look_090 gkmovenear_idlemidturn_022 gkdropball_3_3_fast gkpunch_f02_3_0_y10 autoMove_08_ragged45_slant_loop_3_3_mid dm_oop_ballcome_f090_side_3_3_run_f090 dm_oop_ballcome_handup_one_far_f045_idle_0_1_backslant_v2 coach_1_0_090_cross_arms head_y09_jostle_f_0_0_000_act097 new_dribblerun_4_4_f090_out autoMove_02_reverse_stop_leftfront_rightback_1_1_STEP_near_gabriel autoMove_32_go_to_3_3_nea

OFFSET=0xa361e2 TERM=turn
CONTEXT=oblem. Ignoring this. Host:%s Host: %s%s%s:%d Invalid status line Sunday client_reset, will rewind reader client reader needs rewind before next request Could only read %ld bytes from the input File already completely uploaded client returned ERROR on write of %zu bytes SOCKS-PROXYY No error TFTP: Illegal operation proxy handshake error Credentials was passed in the URL when prohibited Bad fragment No valid port number in connect to host string (%s) Expected %02x%02x but got %02x%02x # 25 ftp. dict ..? ue4 ALPN: server did not agree on a protocol. Uses default. No SSLv2 support No SSLv3 suppor

OFFSET=0xa367ea TERM=turn
CONTEXT=intValue03 p1_length_min touch0 forceLowLob defenceSideAdjustAngleXZMax heightForDistMax_high ballArrivalFastSec ballBound naturalPassget adjustPassGetSpeed manualPassAngleYBase searchLengthMax_fly adjustSetplay adjustSlideMoveSpeed checkReturnDist checkReturnDistX cornerkickDefenceMFSide coverLimitXRate defenceFormationTest1 dfLineWidth_Corner freeKickAdjustRateZ_FW lengthOf mfPushUpRate minDistMF_FW TriMic_RightPitch1_CenterMic .uasset demo/ a.PESSimulateHair.ForceDisableBoneSim 1 match_tutorial_load match_tutorial to cpk_dat/test/flow/ STATE_POST_FADE_IN FlowUnLockInterruption F_LeftCam MatchCo

OFFSET=0xa367fa TERM=turn
CONTEXT=ngth_min touch0 forceLowLob defenceSideAdjustAngleXZMax heightForDistMax_high ballArrivalFastSec ballBound naturalPassget adjustPassGetSpeed manualPassAngleYBase searchLengthMax_fly adjustSetplay adjustSlideMoveSpeed checkReturnDist checkReturnDistX cornerkickDefenceMFSide coverLimitXRate defenceFormationTest1 dfLineWidth_Corner freeKickAdjustRateZ_FW lengthOf mfPushUpRate minDistMF_FW TriMic_RightPitch1_CenterMic .uasset demo/ a.PESSimulateHair.ForceDisableBoneSim 1 match_tutorial_load match_tutorial to cpk_dat/test/flow/ STATE_POST_FADE_IN FlowUnLockInterruption F_LeftCam MatchControlListener >>

OFFSET=0xa36ad0 TERM=turn
CONTEXT=P] time up reason ball is myside for long time RetryAuto_PK_SPA_CANCEL_CHECK_score%d cpk_dat/common/anime/Mbinfo/bin/CameraPickupInfo.bin [FaceHand] LayerUpdate closeUpFaceHandUse=%d m_moveLayerAnimeTimer=%f GetTimeUpAnime camera_person_turn_0_0 demo_move_0_1_1 demo_gutsKneel_3_0 demo_miss_droop_0_1_0 demo_idle_hip_1_0 dm_oop_beckon_180_parallel_2_1_side demo_coop_talk_2 throw_under_0_0_nearline throw_under_0_0_fast_cancel seamless_pass_relax blockfront_0_0_y05_shoot_reaction_v2 fall_upbody_0_0_front_move stagger_ballhit_belly_3_3_quickly gkfall_punch_0_0_r corner_defence_idle demo_move_tired_0

OFFSET=0xa3b20b TERM=turn
CONTEXT=yname failed to construct for eight newline vertical-line lower G:\RenderPlat\Engine\Source\ThirdParty\PhysX3\PhysX_3.4\Source\PhysX\src\NpPhysics.cpp Particle system creation failed. Use PxRegisterParticles to register particle module: returned NULL. G:\RenderPlat\Engine\Source\ThirdParty\PhysX3\PhysX_3.4\Source\compiler\cmake\android\..\..\..\PhysX\src/NpPtrTableStorageManager.h static const char *physx::shdfnd::ReflectionAllocator<physx::NpCloth>::getName() [T = physx::NpCloth] NpScene.solve PxScene::flushSimulation(): This call is not allowed while the simulation is running. Call will be igno

OFFSET=0xa3fce5 TERM=turn
CONTEXT=straintCanvas SPerspectiveHitTesterWidget Coach_Void Touch is disable condition, so %s is running. [TextInput] OnTextCommited, UUiTextInputBase::OnTextCommited AddWindow to an unregistered level %s AWindowManager::GetFlowMadeWindow() return %s ==========Current Windows========== [WinManager] AWindowManager::OnReactivateApplication AMovieManager::UnloadStreamingMovieImpl PlayMenuAnimationWithAnalyzer EAudiInstancePartsType::CAP EAudiCommonType FaceShirtsID ClipHismcInstance DirNum PlaneNo PlacementInterval CalcSeatInfo AreaType TeamSeatNums TeamFloorSeatRandomThresholds GetCommonTypeVariati

OFFSET=0xa429f1 TERM=turn
CONTEXT=EMenuMyClubPlayerDetailHexParamInfoSelect::MENU_MYCLUB_PLAYER_DETAIL_HEX_PARAM_INFO_SELECT_SPD EMenuMyClubPlayerDetailBasicInfoType::MENU_MYCLUB_PLAYER_DETAIL_BASIC_INFO_TYPE_NONE GetPlayerOffenceParamTypeList SetUIAnimationLast IsForwardReturn RootWidget EMenuOneTimeCmnType::ASSET_SHOP EUESessionErrorCode::E_REQUEST_PARAMETER_ERROR MaterialKey backgroundID DeactivateClose ECmnControllerBtn::R2 ECmnControllerBtn::A bIsDestructive OnNewsCursorDownAnimEndEvent OnNewsCursorUpAnimEndEvent SetJumpTextFromStr EUiCmnHeaderBtnType::Present EUiCmnHeaderRightType EUiIconItemType::SpecialScout ECloseButtonKi

OFFSET=0xa431c2 TERM=turn
CONTEXT=ertyFlags, TypeIndex, &TypeIndex) setText %s() CoreUObject Camera MeshEmitterDynamicParameter UserDefinedEnum FlushNetDormancy LiveStreamVoice AssetObjectProperty execLetDelegate execTrue UObjectBaseInit ELocalizedTextSourceCategory EAppReturnType::Cancel EAppReturnType::Ok EUnit::Lightyears EUnit::KilometersPerHour EUnit::Ounces EUnit::Stones EUnit::Kilohertz EUnit::Megahertz PF_FloatRGBA PF_ATC_RGBA_E PF_L8 PF_R32G32_UINT PF_ETC2_RG11_EAC PF_MAX ELogTimes::None ClassNames Up Zero Two NumPadFour Gamepad_RightThumbstick Vive_Right_Trackpad_Click MixedReality_Left_Menu_Click MixedReality_Left_Trac

OFFSET=0xa431d9 TERM=turn
CONTEXT=TypeIndex) setText %s() CoreUObject Camera MeshEmitterDynamicParameter UserDefinedEnum FlushNetDormancy LiveStreamVoice AssetObjectProperty execLetDelegate execTrue UObjectBaseInit ELocalizedTextSourceCategory EAppReturnType::Cancel EAppReturnType::Ok EUnit::Lightyears EUnit::KilometersPerHour EUnit::Ounces EUnit::Stones EUnit::Kilohertz EUnit::Megahertz PF_FloatRGBA PF_ATC_RGBA_E PF_L8 PF_R32G32_UINT PF_ETC2_RG11_EAC PF_MAX ELogTimes::None ClassNames Up Zero Two NumPadFour Gamepad_RightThumbstick Vive_Right_Trackpad_Click MixedReality_Left_Menu_Click MixedReality_Left_Trackpad_Click MixedReality

OFFSET=0xa48079 TERM=turn
CONTEXT=op_lineback_000_mid_delay autoMove_00_bodyangle_00_90_f90_00_3_3_mid_michael autoMove_00_bodyangle_00_90_f90_00_3_3_STEP_mid_michael catchrun_3_3 autoMove_01_reverse_loop_parallel_side_2_2_STEP_mid_michael autoMove_01_reverse_loop_parallel_turn_2_2_mid_michael autoMove_01_reverse_loop_slant_backslant_3_3_mid_michael new_dribble_0_4_090_in autoMove_02_reverse_stop_leftside_rightside_3_3_near_gabriel autoMove_05_zigzag135_front_loop_1_1_STEP_near_gabriel autoMove_30_turn_move_1_1_CRANK_near_gabriel autoMove_01_dribble_reverse_loop_side_2_2_STEP_near_gabriel dash_06_slant_1_4_run_Oriul gkmovemid_Catc

OFFSET=0xa4815e TERM=turn
CONTEXT=p_parallel_turn_2_2_mid_michael autoMove_01_reverse_loop_slant_backslant_3_3_mid_michael new_dribble_0_4_090_in autoMove_02_reverse_stop_leftside_rightside_3_3_near_gabriel autoMove_05_zigzag135_front_loop_1_1_STEP_near_gabriel autoMove_30_turn_move_1_1_CRANK_near_gabriel autoMove_01_dribble_reverse_loop_side_2_2_STEP_near_gabriel dash_06_slant_1_4_run_Oriul gkmovemid_CatchMove_2_2_ball nearDribble_04_1_dribble_burst_1_4_f045_y0_oriul nearDribble_04_1_dribble_burst_2_4_180_y0_oriul gkgoalkick_Quick_short_0_0_000_right dm_oop_lineup_handup_135_walk_1_1_walk_000 gkdeflectlate_s02_0_0_y02 new_dribble

OFFSET=0xa48bab TERM=turn
CONTEXT=Move_06_01_gkmovenear_Sidestep_Angle5_2_2 autoMove_07_01_gkmovenear_Sidestep_Angle5_2_2 enum_dummy463 enum_dummy524 enum_dummy549 enum_dummy582 enum_dummy598 enum_dummy609 enum_dummy643 enum_dummy650 block_0_0_y01_000_act071 gkmovenear_stopturn_1_0 gkrise_sideways_l_0_0_060_hand LongVersion_161108_F105_t01_Michael_02 enum_dummy658 /Game/Assets/character/Gloves/SK_g%03d_Glove.SK_g%03d_Glove base_d_iki_karui base_itagari_odoroki bitter_brwnit_grit_eyhc pose_smile_laugh_L_02 pose_sorrow_dejection_L_02 pose_sorrow_pain_grit_02_open_eye pose_sorrow_pain_grit_03_open_eye pow_brwup_unnos_in wor_brwnit_pu

OFFSET=0xa49971 TERM=turn
CONTEXT=_OUT CRRECT] %.2fm -> %.2fm dm_oop_pointing_045_run_2_2_run dm_miss_idle_0_1_walk_angry_high_0 demo_pfm_rotationjumpguts_3_3_l demo_pfm_provocation_3_3_l puntkick_side_0_0_fast judge_whistle_2_2 linesman_offside_cancel_fromflagup linesman_turn_0_1 blockfront_0_0_y04_shoot_reaction blockfront_0_0_y06_shoot_reaction fall_lowbody_4_0_v3_l stagger_lowbody_3_3_tackle_m3_r goalturn_faceup demo_glad_3_0_000_5 demo_gk_glad_22 demo_angry_hurry_8 demo_miss_3_1_bendback_045_1 demo_miss_0_1_droop_090_1 demo_miss_3_1_face_135 demo_miss_0_1_hip_045_2 demo_gk_miss_8 demo_appeal_0_0_at135_1 demo_appeal_0_0_at135

OFFSET=0xa499f8 TERM=turn
CONTEXT=m_provocation_3_3_l puntkick_side_0_0_fast judge_whistle_2_2 linesman_offside_cancel_fromflagup linesman_turn_0_1 blockfront_0_0_y04_shoot_reaction blockfront_0_0_y06_shoot_reaction fall_lowbody_4_0_v3_l stagger_lowbody_3_3_tackle_m3_r goalturn_faceup demo_glad_3_0_000_5 demo_gk_glad_22 demo_angry_hurry_8 demo_miss_3_1_bendback_045_1 demo_miss_0_1_droop_090_1 demo_miss_3_1_face_135 demo_miss_0_1_hip_045_2 demo_gk_miss_8 demo_appeal_0_0_at135_1 demo_appeal_0_0_at135_2 demo_appeal_3_1_045 demo_appeal_hurry_22 demo_contact_pain_045_1 demo_contact_pain_135_1 demo_gk_praise_fallside_1 demo_praise_hurry

OFFSET=0xa4dbde TERM=turn
CONTEXT=PST BackWaitTime Funcs CheckBuildSwitch CheckOutofplayReason CheckHalfZone CheckPlayerNumAbilityValueDetail CheckRestartStep CheckFreeKickArea CheckFoulKind CheckLooseBallVariousData CheckSituationCrossFailed CheckPassReceiving CheckCountReturnPass CheckNearPenaltyAreaLine CheckShortPassDist MatchStatus LineOption SoundCommonConditionLastShoot PlayerDataMyClub InstructionData CoachInstructionData CoachVariousData STEPUP CENTER FUNC STATUS_FINISHED SCENE_TROPHY SCENE_PICKUP 03_D 10_A EX2ND RAREA_D FIELD_NEAR SHORT TO_RIGHT CUP_TUR CUP_BRA_SP LG_CHL LG_SCO EX01 OUTPLAY STEAL_GOALAREA JUMP STRONGER_F

OFFSET=0xa4e28c TERM=turn
CONTEXT=T = physx::NpPtrTableStorageManager::PtrBlock<64>] static const char *physx::shdfnd::ReflectionAllocator<physx::NpRigidDynamic>::getName() [T = physx::NpRigidDynamic] Articulation link initialization failed due to joint creation failure: returned NULL. PxAggregate: can't add articulation link to aggregate, only whole articulations can be added setVisualizationParameter: value must be larger or equal to 0. PxScene::setContactModifyCallback() not allowed while simulation is running. Call will be ignored. PxScene::setBroadPhaseCallback() not allowed while simulation is running. Call will be ignored. 

OFFSET=0xa4f5ff TERM=turn
CONTEXT=limole-per-liter bit picometer -Subnormal -Infinity calendarData adobe resource.frk/ NORM_SPACE RAW_NORM_SPACE RAW_POINT_SIZE RAW_SUBSCRIPT_SIZE OtherBlues StartKernData Slant Bold Italic -syrj px-hant-mo -lux unexpected zlib return code RGB color space not permitted on grayscale PNG gray[16] color-map: too few entries bad data option (internal error) invalid with alpha channel tEXt: invalid keyword Unrecognized unit type for pHYs chunk ()Landroid/view/Display; ATrace_endSection Swappy::EGL CriMvPly: HnObj ofs_byte E12021601M:num_seekblock is short. E05063027M:Chunk is not same to one 

OFFSET=0xa5b35c TERM=turn
CONTEXT= block_2_0_y01_000 gkmoveSeriesB_Front_2_2_90 js_run_3_3_000_guard_side_set003_df_draw_act064 gkoverthrow_0_0_hard_045 gksidethrow_3_0_cancel js_run_3_3_000_push_away_v2 autoMove_03_crank90_loop_1_1_mid autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_STEP_mid coach_0_0_000_cross_arms dm_oop_ballcome_000_walkback_1_3_runback dm_oop_lineup_f090_mid_delay autoMove_00_bodyangle_00_90_180_00_1_1_mid_michael autoMove_01_dribble_reverse_loop_slant_backslant_3_3_mid_gabriel autoMove_07_ragged45_front_loop_1_1_STEP_mid_michael autoMove_07_ragged45_front_loop_2_2_STEP_near autoMove_08_ragged45_slant_loo

OFFSET=0xa5b4ff TERM=turn
CONTEXT=01_dribble_reverse_loop_slant_backslant_3_3_mid_gabriel autoMove_07_ragged45_front_loop_1_1_STEP_mid_michael autoMove_07_ragged45_front_loop_2_2_STEP_near autoMove_08_ragged45_slant_loop_1_1_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_mid_michael coach_1_1_f090_cross_arms coach_1_1_f090_cross_arms_position_up_high autoMove_32_go_to_2_2_near Liftup_passcatch_0_0_y5 feintrun_bodyfake_front_3_3_000_y0_ver01 autoMove_01_reverse_loop_slant_backslant_3_3_near_gabriel autoMove_02_reverse_stop_leftside_rightside_2_2_STEP_near_gabriel autoMove_02_reverse_stop_rightfront_leftback_3_3_STE

OFFSET=0xa5b866 TERM=turn
CONTEXT=_near_gabriel autoMove_02_dribble_reverse_stop_leftfront_rightback_2_2_STEP_near_gabriel gkblock_lie_s02b01_0_0_y04_090 gkdeflect_f05_3_0_y00_090 gkdeflect_f05_3_0_y02_090 traprun_arc_3m_3m_f045_y0_in_act064 dml_goal_celebrate_0208 dash_05_turn_4_4_045_CRANK_Ortega pk_enclose_hiza dml_goal_celebrate_0069 dml_goal_celebrate_0077 loop_3_3_000_run_near_act109 D_PES_20251203_K06_001_kubo_01_Fcut001 dml_goal_celebrate_0101 StabilizerCam_idle_0_2_runsideways_R StabilizerCam_walkside_1_0_idle_L StabilizerCam_walkside_1_1_L dm_oop_pointing_000_mid_delayside_1_1 dm_oop_pointing_000_run_2_2 dm_oop_pointing_

OFFSET=0xa5becf TERM=turn
CONTEXT=000 enum_dummy159 enum_dummy180 LongVersion_200127_F002_t01_Oriul LongVersion_200127_F003_t01_Gabriel LongVersion_200127_F004_t01_Ortega enum_dummy271 enum_dummy278 autoMove_06_zigzag180_side_loop_1_2_3_act079 autoMove_40_circle_short_side_turn_2_2_bodyangle_keep_act080 dash_04_turn_4_4_parallel_150_act079 dash_06_slant_2_4_run_act068 set_ball_hand_3_0_090 enum_dummy292 dm_oop_gk_riseup_0_0_sideways_Glad_000_v02 dm_oop_angry_1_3_180_act064 dm_oop_praise_1_3_090_atf090_act071_01 StabilizerCam_idle_0_2_run enum_dummy345 LongVersion_201123_F016_t01_act068_01 LongVersion_201123_F026_t01_act071_01 Long

OFFSET=0xa5bef6 TERM=turn
CONTEXT=sion_200127_F002_t01_Oriul LongVersion_200127_F003_t01_Gabriel LongVersion_200127_F004_t01_Ortega enum_dummy271 enum_dummy278 autoMove_06_zigzag180_side_loop_1_2_3_act079 autoMove_40_circle_short_side_turn_2_2_bodyangle_keep_act080 dash_04_turn_4_4_parallel_150_act079 dash_06_slant_2_4_run_act068 set_ball_hand_3_0_090 enum_dummy292 dm_oop_gk_riseup_0_0_sideways_Glad_000_v02 dm_oop_angry_1_3_180_act064 dm_oop_praise_1_3_090_atf090_act071_01 StabilizerCam_idle_0_2_run enum_dummy345 LongVersion_201123_F016_t01_act068_01 LongVersion_201123_F026_t01_act071_01 LongVersion_201123_F028_t01_act068_01 LongV

OFFSET=0xa5f0eb TERM=turn
CONTEXT=aL7+97y0/INKa/ovULwzGTlunyIFi 44iv4DzixU5N3pBzb5cI6ftqQhC+0R1zULwCrKoRxEX26CuI/ZkI8P20DCCDN516 BVYMH4rOt3mF9VafazdTg7cCAwEAAQ== -----END PUBLIC KEY----- getPrice adjust_id added_items psn_entitlement_id receipt_list CmdSendAdjustParam.php turn_task PrivilegeChecker r\d+ UtilHashTask GetSOCModelName grpc.max_send_message_length grpc.max_connection_idle_ms grpc.max_reconnect_backoff_ms grpc.inhibit_health_checking Failed to set credentials to rpc. G:\PES22HC\Dev-600Series\Source\Shared\basic\ext\grpc\grpc\src\cpp\client\client_context.cc head_.Load(MemoryOrder::RELAXED) == &stub_ fd Error %p is ful

OFFSET=0xa60fb6 TERM=turn
CONTEXT=rCompe Online/EvCompe/MlEvent/Match/ProcMlEventPreSkipMatch Online/EvCompe/MlEvent/Match/ProcMlEventPreFansAfterMatch confirm_konami_id pause_quick_goal tutorial_failure match_pause match_result_pk_match_start to_loop_reward capture_demo return_tournament StrikeArenaTest expCurrentLevel additionalSkillList ExecuteConsoleCommand "gc.TimeBetweenPurgingPendingKillObjects 10000000" SaveSystemIconLoader sa_list.xml SA_C_NMB_E00 SA_C_NMB_E15 SA_C_NMB_E21 SA_C_NMB_E23 SA_C_NMB_E46 SA_C_NMB_E66 SA_C_NMB_E76 SA_C_NMB_E79 SA_C_NMB_E86 SA_C_NMB_E93 SA_C_NMB19 SA_C_NMB24 SA_C_NMB30 SA_C_NMB39 SA_C_NMB66 SA_C_

OFFSET=0xa6bbd3 TERM=turn
CONTEXT=ternal TLM_VolumetricDirectional AspectRatio_MaintainXFOV V1_Color LocationQuantizationLevel SwarmDebugOptions bShadowIndirectOnly MaxLinearHardSnapDistance NonDirectionalInscatteringColorDistance VSize bIncludeASCIIRange ExtendBoxBottom ReturnToMainMenuHost GetGlobalTimeDilation SetSubtitlesEnabled SetViewportMouseCaptureMode DamageRadius ObjectClass ArcParam IsScreenResolutionDirty bUseDynamicResolution StartPerformanceSnapshots HPP_World NextDebugTarget MaterialU SecondPoint EImportanceWeight::Alpha NextSobolFloat ExcludedAutocorrectOS MapBuildDataIds InstancedStaticMeshInstanceData bColorCurve

OFFSET=0xa744cb TERM=turn
CONTEXT=e_master_secret SSL_COMP_add_compression_method SSL_use_certificate_ASN1 SSL_use_PrivateKey_ASN1 SSL_write_ex tls12_copy_sigalgs tls_construct_encrypted_extensions tls_parse_ctos_cookie tls_process_cke_srp bad change cipher spec bad data returned by callback bad srtp mki value bio not set encrypted length too long no required digest sct verification failed sslv3 alert bad record mac unable to load ssl3 md5 routines unknown ssl version comp SSLOK TWFIN TRCKU unsupported extension ed25519 Training/TrainingLoad Match/OpeningDemo/OpeningDemoMatchSetup Match/Gimmick/GimmickNewControlGuide MyClub/MyTea

OFFSET=0xa747a4 TERM=turn
CONTEXT=ordEvent/ProcEvCompeFastGoalRankingSelf Online/EvCompe/TourPvp/ProcEvCompeOutFromGroupMatchRoot Online/MatchPass/ProcMatchPassBack Online/MatchPass/ProcMatchPassBackFromLobby Settings/Lang/ProcInGameTextLoad side_setting current_location return_tour_pvp isLicenceTexture initialBoosterId ExecuteConsoleCommand "gc.MinGCClusterSize 1000000" ExecuteConsoleCommand "gc.MinGCClusterSize 5" a.PESPlayer.DisableTattoo true SA_C_NMB_E49 SA_C_NMB_E77 SA_C_NMB_E85 SA_C_NMB07 SA_C_NMB52 SA_C_NMB80 SA_C_NMB97 Failed to read Element name Error parsing Declaration. Original %s_%s_%s SA_PP3 BackWaitBureHaba Func Ch

OFFSET=0xa74db1 TERM=turn
CONTEXT=ndroid/common/Applilink pc0101 E2013013001 E2020052502 sendEventCustom 001001110111110 AliveList pol tha SetTmpdbThread cpk_dat/common/etc/pesdb Player.bin PlayerVariationDetail.bin GetTotalBytesToDownload unexpected_handler unexpectedly returned VTT for nullptr <char, std::char_traits<char> string literal struct condition_variable::wait: mutex not locked __next_prime overflow ctype_byname<wchar_t>::ctype_byname failed to construct for exclamation-mark four Fasttracker PxRigidActor::detachShape: shape is not attached to this actor! PxRigidDynamic NpSceneQueries.sceneQueriesStaticPrunerUpdate PxS

OFFSET=0xa7abe6 TERM=turn
CONTEXT=CmdJoinRoom IsStrikeArenaTimeOut SetReady ELobbyRoomAlertKind::None ELobbyRoomAlertKind::EventEnd UpdatePlayer RequestAlertDelegates ELayoutMatchRoomMainMenuCoopListParts::Exist DispCopyButton PrevMessageId BonusTimeStr IsKicked IsWaitingReturnFromMatch ELobbySideSelectSideAnime::NoChange ELobbySideSelectMenuState::Finished m_arrayUserCell EMenuMailboxReceiveResult::RECEIVE_RESULT_FAIL_BREAKDOWN EMenuMailboxSortType::MAILBOX_SORT_ID GetCoinStr GetGpStr GetPresentStr UpdateUnreadNewsNum rarity receiveResult pBpWidget OnPressedLCrossDownButton OnPressedLCrossUpButton StartDemo EMenuMatchKickerSelect

OFFSET=0xa815e8 TERM=turn
CONTEXT=kcatchslide_f03_3_0_y10_090 dm_miss_sidestep_1_1_walk_angry_090 gkseeoff_light_0_1_y11_090 layer_wipe_sweat trap_0_0_000_y6_shoulder_rest_ver21 kick_mid_3_3_adjust_y0_f022 autoMove_41_parallel_to_run_3_3m_far_act097 passGetMove_03_parallel_turn_3m_3m_045_act064 dm_goal_jog_2_4_dash_090 dm_oop_gk_glad_idel_guts_under_0_1_000 js_run_2_2_000_guard_side_set007_df_act064 gkmoveSeriesA_Side_1_1_Reverse kick_mid_0_0_infront_y0_045_punch fall_upbody_3_0_090_hold_waist js_run_3_3_000_guard_side_set008_df_act068 js_run_3_3_000_guard_side_set008_of_act064 stagger_upbody_3_3_090_interrupt_lose gkdeflect_f05_3

OFFSET=0xa81b5f TERM=turn
CONTEXT=3_dribble_crank90_loop_1_1_STEP_near_gabriel autoMove_05_dribble_zigzag135_front_loop_1_1_STEP_near_gabriel new_dribble_0_4_f090_out autoMove_32_go_to_2_2_near_gabriel autoMove_35_TURNCANCEL_Slant_3_3_f090_090_180_STEP_near_gabriel dash_05_turn_4_4_045_CRANK_Oriul dash_05_turn_4_4_090_CRANK_Oriul autoMove_01_dribble_reverse_loop_slant_backslant_2_2_STEP_near_gabriel gkmovehigh_idle_0_0_045_ball gkdeflectlate_s04_0_0_y10 gkblockcover_f01_0_0_y00 dribblerun_arc_3_3m_67_y0_in_act097 traprun_arc_3_3m_090_y0_in_act064 dash_05_turn_4_4_090_CRANK_Ortega pk_enclose_harai dml_goal_celebrate_0007 dml_goal_c

OFFSET=0xa81b80 TERM=turn
CONTEXT=ear_gabriel autoMove_05_dribble_zigzag135_front_loop_1_1_STEP_near_gabriel new_dribble_0_4_f090_out autoMove_32_go_to_2_2_near_gabriel autoMove_35_TURNCANCEL_Slant_3_3_f090_090_180_STEP_near_gabriel dash_05_turn_4_4_045_CRANK_Oriul dash_05_turn_4_4_090_CRANK_Oriul autoMove_01_dribble_reverse_loop_slant_backslant_2_2_STEP_near_gabriel gkmovehigh_idle_0_0_045_ball gkdeflectlate_s04_0_0_y10 gkblockcover_f01_0_0_y00 dribblerun_arc_3_3m_67_y0_in_act097 traprun_arc_3_3m_090_y0_in_act064 dash_05_turn_4_4_090_CRANK_Ortega pk_enclose_harai dml_goal_celebrate_0007 dml_goal_celebrate_0075 layer_gk_free_Bothh

OFFSET=0xa81c7e TERM=turn
CONTEXT=RANK_Oriul autoMove_01_dribble_reverse_loop_slant_backslant_2_2_STEP_near_gabriel gkmovehigh_idle_0_0_045_ball gkdeflectlate_s04_0_0_y10 gkblockcover_f01_0_0_y00 dribblerun_arc_3_3m_67_y0_in_act097 traprun_arc_3_3m_090_y0_in_act064 dash_05_turn_4_4_090_CRANK_Ortega pk_enclose_harai dml_goal_celebrate_0007 dml_goal_celebrate_0075 layer_gk_free_Bothhand_point head_y08_0_0_180_rear dm_oop_pointing_000_runback_2_2 dm_oop_pointing_f045_mid_delayback_1_1 dm_oop_pointing_f090_walk_1_1 F_ActualBattle_191007_F011_t01_Morgun_Fcut004 ActualBattle_181002_F100_t02_Yuujin ActualBattle_191008_FZ006_t01_Jhoan Lon

OFFSET=0xa85069 TERM=turn
CONTEXT=kIoDegradedByDisconnectEnable MultiplaySessionStrategyIoBufferRecvSize FecQueueParityEncoderMaxBufferLength ChannelReceiveBufferMaxBufferLength ActualMatchHzConditionDeterminationEnable ActualMatchHzWithInactiveConditionDeterminationEnable turn_mode Unknown error code. (error code = Wrong credentials. (error code = CMD_SIDE_SELECT CMD_SYNC_MATCHPLAN_DATA_FULL [cnt: NONCE SUCCESS_RESP SoapAction: "%s#%s" specVersion NewRemoteHost </SOAP-ENV:Body></SOAP-ENV:Envelope> ${"TurnEvent":"%s(0x%08x)"} G_TIMEOUT E_MUTEX_PERM E_INVALID_OPS UPNP_DELETE_PORT_FORWARDING_MISS_MATCH ADD -%s command_adaptive_r

OFFSET=0xa853fb TERM=turn
CONTEXT=SSION_TRANSPORT_RTT_COUNT IPV4 PROTO_OPT_HASH REVISION :[ LATENCY_NTL_PUNCHING_PROCESS MEMPEAK_USED_PHYSICAL MEMPEAK_WINDOW_HASH MEMPEAK_MATCH_STATE SURVEY_ANSWER_0 RX_RLOSS_RATE_MIN getCountryCode CmdUnsubscribeGrpc.php CmdWatchNotice.php turn_time_limit try_count WiM enable_indicator_stats_for_answered mini_conn_stats conn_report %s_%s PS3 grpc.xds_fallback_timeout_ms grpc.xds_failover_timeout_ms Def_Online_gRPC_Log_Level G:/PES22HC/Dev-600Series/Source/Shared/basic/ext/grpc/grpc/include/grpcpp/impl/codegen/async_stream_impl.h false && "It is illegal to call GetSendStatus on a method which " "ha

OFFSET=0xa87755 TERM=turn
CONTEXT=DialogStatus:ASSET_PACK_CONFIRMATION_DIALOG_APPROVED [%s] pc3611_optional tuto jp/konami/android/common/WebBrowser Cellular data request failed due to null Android Activity. LaunchReviewFlow android_activity param is null. _Z covariant return thunk to basic_ostream char16_t _Unwind_Reason_Code __cxxabiv1::__gxx_personality_v0(int, _Unwind_Action, uint64_t, _Unwind_Exception *, _Unwind_Context *) locale constructed with null time_put_byname failed to construct for moneypunct_byname failed to construct for backspace left-square-bracket blank Scream Tracker 3 PxMaterial::setRestitution: Invalid 

OFFSET=0xa87b08 TERM=turn
CONTEXT=flectionAllocator<physx::PxBounds3>::getName() [T = physx::PxBounds3] PxShape::setLocalPose: Shape is a part of pruning structure, pruning structure is now invalid! PxShape::getMaterialFromInternalFaceIndex received 0xFFFFffff as input - returning NULL. PxShape::setFlag(s): shapes cannot simultaneously be trigger shapes and simulation shapes. Call to PxCloth::setCollisionPlanes() not allowed while simulation is running. Call to PxCloth::setSelfCollisionStiffness() not allowed while simulation is running. Call to PxCloth::setSimulationFilterData() not allowed while simulation is running. PxParticle

OFFSET=0xa89f13 TERM=turn
CONTEXT=sPlaylistParser_GetUriIndexByuTime(%f) failed on criVodStm_Play. E2018122607:CriAesDecryptorAndroid Instance in java layer(jobject) is null. [CriAesSegmentsDecryptor] Failed to malloc a handle. [CriAesSegmentsDecryptor] The get_url api returns invalid status(%d). Deal it as DO_DEFAULT. AndroidThunkJava_GetFontDirectory Z ()[I GEngine->ParseCommandline() InitTime ResolutionHeight RenderTarget TransportType GetFilteredBone SetParticleNeighborCount LinearToIndex FieldBounds MovieSceneNiagaraIntegerParameterSectionTemplate ENiagaraSystemSpawnSectionEndBehavior::SetSystemInactive SetDestroyOnSystemF

OFFSET=0xa8d46d TERM=turn
CONTEXT=VotingId ESettingAvatarKind::E_SETTING_AVATAR_KIND_BG GetIndexFromAvatarInfoBG GetIndexFromAvatarInfoPlayer rawList WaitTag IsKonamiIdConnectError GetStrId ECmnPauseIconType::SIDE_SELECT ETeamSelectStep GetAssociationList GetMemberData IsReturnPrev ETeamSelectLeagueKind::TEAM_SELECT_LEAGUE_MAX ETeamSelectAssociation::TEAM_SELECT_SOUTH_AMERICA Send ECompeEmblemAssociation::COMPE_EMBLEM_ASIA_OCEANIA EEventUserAgeCategory::U22 EMenuPointIcon::CampaignPoint EMenuCommonValid::Num GetFStringNextFlow GetNextPartStr EDataLinkageStatus SpawnDetailViewDataLinkNotes selectIdx EMenuEulaAgreeFlowEvent::NONE EM

OFFSET=0xa9109d TERM=turn
CONTEXT=nit NamedTransform MinKeys GetLinkedAnimGraphInstancesByTag CurrentSkeleton BranchingPointMarker InertializationBoneDiff EEvaluatorDataSource::Type AnimPhysTwistAxis::AxisY bForceRootLock TrackBoneNames BakedStateExitTransition TransitionReturnVal EAdditiveAnimationType ENotifyFilterType::Type BCS_ParentBoneSpace ETemperatureSeverityType::Bad ScreenSize bPrompt EPrimaryAssetCookRule::Unknown AssetMapping AtmospherePrecomputeParameters SunMultiplier TransmittanceTexture EAttenuationShape::Capsule EAudioFaderCurve EAudioComponentPlayState::Stopped VolumeModulationMin EMonoChannelUpmixMethod::Linear 

OFFSET=0xa93fc0 TERM=turn
CONTEXT=7_jostle_0_0_f090_side_dive head_y09_0_0_000_rear head_y09_shoot_0_0_000 new_idle_0_4_run_225_act087 feint_reboundstep_0_4_045_y0_instep_act064 tacklefoot_mid_0_0_f067_act064 js_back_1_1_loop_guard_back_sub js_idle_0_3_loop_guard_back_main_turn_180 kick_long_0_0_instep_y2_090_topspin kick_long_0_0_outside_y0_f045_curve kick_long_3_0_infront_y0_090 kick_long_3_0_infront_y0_090_late_2 kick_mid_0_0_inside_y0_045_rear kick_mid_0_0_inside_y4_000 kick_mid_0_0_inside_y4_f045 kick_mid_0_0_outside_y0_f135_rear_far kick_mid_3_0_inside_y2_f045 kick_short_0_0_inside_y0_135_late_sidestep js_idle_0_0_135_guard_

OFFSET=0xa946f1 TERM=turn
CONTEXT=de_3_0_after_y06 feintrun_stepkick_3_4_f000_y0_ver23 enum_dummy9 block090_0_0_y00_000_far_act079 blockhead_0_0_y04_000_down sliding_3_0_022_parallel_jostle_L_kickout dm_oop_gk_cheer_idle_thumbsup_0_0_000 dm_oop_gk_glad_riseup_sideways_guts_turn_0_1_f135 js_run_1_1_000_guard_side_set006_df_act064 head_y07_sidle_chest_2_0_f090_shed head_y09_0_0_090_side_v2 gkunderthrow_0_0_fast_cancel feintrun_lift_2_3_f045_sidenear_y2_far_ver12 autoMove_05_zigzag135_front_loop_2_2_mid autoMove_10_bodyangle_keep_circle_smallturn_front_1_1_mid dm_oop_ballcome_f090_side_3_3_runback_090 dm_oop_beckon_000_walkback_1_3_r

OFFSET=0xa94800 TERM=turn
CONTEXT=ard_side_set006_df_act064 head_y07_sidle_chest_2_0_f090_shed head_y09_0_0_090_side_v2 gkunderthrow_0_0_fast_cancel feintrun_lift_2_3_f045_sidenear_y2_far_ver12 autoMove_05_zigzag135_front_loop_2_2_mid autoMove_10_bodyangle_keep_circle_smallturn_front_1_1_mid dm_oop_ballcome_f090_side_3_3_runback_090 dm_oop_beckon_000_walkback_1_3_runback autoMove_04_crank45_loop_3_3_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_v2_mid_michael autoMove_30_dribble_turn_move_3_3_CRANK_mid_gabriel new_dribbleslide180_3_4_f180_sole autoMove_02_reverse_stop_front_back_3_3_STEP_near_gabriel autoMove_00_

OFFSET=0xa948b2 TERM=turn
CONTEXT=135_front_loop_2_2_mid autoMove_10_bodyangle_keep_circle_smallturn_front_1_1_mid dm_oop_ballcome_f090_side_3_3_runback_090 dm_oop_beckon_000_walkback_1_3_runback autoMove_04_crank45_loop_3_3_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_v2_mid_michael autoMove_30_dribble_turn_move_3_3_CRANK_mid_gabriel new_dribbleslide180_3_4_f180_sole autoMove_02_reverse_stop_front_back_3_3_STEP_near_gabriel autoMove_00_bodyangle_00_90_00_3_3_STEP_near_gabriel autoMove_08_dribble_ragged45_slant_loop_1_1_STEP_near_gabriel defenseMove_02_1_2_Match_up_center_EXTRA_1_act082 dash_09_idle_0_4_135_dash

OFFSET=0xa948e4 TERM=turn
CONTEXT=circle_smallturn_front_1_1_mid dm_oop_ballcome_f090_side_3_3_runback_090 dm_oop_beckon_000_walkback_1_3_runback autoMove_04_crank45_loop_3_3_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_v2_mid_michael autoMove_30_dribble_turn_move_3_3_CRANK_mid_gabriel new_dribbleslide180_3_4_f180_sole autoMove_02_reverse_stop_front_back_3_3_STEP_near_gabriel autoMove_00_bodyangle_00_90_00_3_3_STEP_near_gabriel autoMove_08_dribble_ragged45_slant_loop_1_1_STEP_near_gabriel defenseMove_02_1_2_Match_up_center_EXTRA_1_act082 dash_09_idle_0_4_135_dash_Oriul autoMove_02_dribble_reverse_stop_leftside_r

OFFSET=0xa94b2e TERM=turn
CONTEXT=se_stop_leftside_rightside_3_3_STEP_near_gabriel nearDribble_04_1_dribble_burst_0_4_f090_y0_oriul dm_oop_linekeep_walkslant_1_1_walkbackslant_090 new_dribblerun_2_3_f180_y0_sole_act064 new_dribblerun_arc_3_3m_67_y0_in_act097 feintrun_springturn_3_3_f067_y0_in_out_act097 dribblerun_arc_2_3_f90_y0_out_act064 dml_goal_celebrate_0267 js_run_dodge_045_set01_3_3_000_of_act097 dml_goal_celebrate_0099 dml_goal_celebrate_0116 D_PES_20251204_M01_001_morimura_06_Fcut001 dm_oop_pointing_f090_walkback_1_1 dm_oop_pointing_f180_mid_delayside_2_2 dm_oop_waitpose_f045_walkback_1_1 enum_dummy10 ActualBattle_191008_

OFFSET=0xa96274 TERM=turn
CONTEXT=hoot_reaction_v2 blockfront_0_0_y04_shoot_reaction_head blockfront_2_0_y02_shoot_reaction blockside_4_0_y00 fall_upbody_3_0_v2 stagger_air_upbody_3_0 stagger_upbody_3_3 stagger_ballhit_head_0_0_quickly fall_upbody_3_0_interrupt_lose_v2 goalturn_hyper2_2_4 demo_move_1_1_135 demo_move_0_1_045_look demo_move_0_1_135_sweat demo_move_tired_3_0 demo_gk_glad_lie_2 demo_gk_angry_6 demo_angry_hurry_17 demo_miss_0_1_droop_045_2 demo_miss_3_1_droop_090_2 demo_miss_0_1_head_090 demo_miss_0_0_allfours demo_miss_3_0_allfours demo_appeal_nofoul_045 demo_appeal_hurry_9 demo_appeal_hurry_11 demo_appeal_hurry_16 de

OFFSET=0xa96914 TERM=turn
CONTEXT=4_0_y0_in trapside_l_4_4_y2_in trapside_l_4_4_y4_in_mid trapside_l_3_3_y2_in_mid trapside_r_0_3_y0_in_angle trapside_r_0_3_y2_in trapside_r_3_4_y0_out tackle_3_0_mid_parallel_v2 trapstep_000_3_3_y0_out trapstep_f090_3_3_y0_in demo_gk_angry_turn_135 demo_gk_glad_lie_16 springturn_3_3_l trapchopside_r_3_4_y0_out_arc TO INJURY_STANDUP(INJURY_LOOP) [feint_check]feint_ok feintKind=%d ANM_DM_MISS_IDLE_0_1_WALK_HEAD_045 cpk_dat/common/anime/playerID/bin/Derivationdatatable.bin [Command] ControlMode [%s] (enemy pass touch timer under 1.5sec and bad pos or body angle) [Command] ControlMode [%s] (freeki

OFFSET=0xa96937 TERM=turn
CONTEXT=side_l_4_4_y4_in_mid trapside_l_3_3_y2_in_mid trapside_r_0_3_y0_in_angle trapside_r_0_3_y2_in trapside_r_3_4_y0_out tackle_3_0_mid_parallel_v2 trapstep_000_3_3_y0_out trapstep_f090_3_3_y0_in demo_gk_angry_turn_135 demo_gk_glad_lie_16 springturn_3_3_l trapchopside_r_3_4_y0_out_arc TO INJURY_STANDUP(INJURY_LOOP) [feint_check]feint_ok feintKind=%d ANM_DM_MISS_IDLE_0_1_WALK_HEAD_045 cpk_dat/common/anime/playerID/bin/Derivationdatatable.bin [Command] ControlMode [%s] (enemy pass touch timer under 1.5sec and bad pos or body angle) [Command] ControlMode [%s] (freekick & coach cursor) [Command] KEEP 

OFFSET=0xa97a43 TERM=turn
CONTEXT=ATE_INFO sound_data CmdStartMatching.php event_list player_id_list CMD_GET_EVENT_COMPE_CAMPAIGN_LIST STATE_PUBLISHED STATE_CALCULATING CmdSendMlEventRestart.php CmdIsFirstLeague.php CmdSetLeaguePerformanceDisped.php CmdGetRoomList.php CmdReturnRoom.php CMD_GET_MYCLUB_ACHIEVEMENT_INFO_LIST skillcard_id_list CMD_GET_MYCLUB_PROCURABLE_GAMEPLAYERLIST is_task_list CMD_SELL_MYCLUB_GAMEPLAYER effect_list time_zone CmdGetStrikeArenaInfo.php CMD_SET_STRIKE_ARENA_COSTUME d_user_compe_id compe_format_type enable_entry_limit relationship CMD_SET_FAVORITE_PLAYER CmdRequestKidParentalAgreement.php NORMAL_4 CMP 

OFFSET=0xa99ede TERM=turn
CONTEXT=share tls_construct_stoc_supported_versions tls_process_cke_gost bad length cookie gen callback failure record length mismatch request sent ssl session id callback failed tlsv13 alert certificate required unexpected record unknown cipher returned wrong ssl version wrong version number Ciphersuites ECDHSingle Peer RequestPostHandshake SSLv3/TLS read server done DTLS1 write hello verify request TWSKE Intro/IntroEnd Match/Pause/MatchPauseWaitView Match/Setup/MatchFTUESetup Tutorial/TutorialPlayEnd Match/PathToGlory/PathToGloryFailureDialogEnd GamePlan/ProcessGamePlanInherit Online/Match/MatchProcessP

OFFSET=0xaa1695 TERM=turn
CONTEXT=aymentKind::EPAYMENT_KIND_SCOUT EMyClubPaymentKind::EPAYMENT_KIND_PLAYER_MAX EMyClubPaymentKind::EPAYMENT_KIND_ML_EVENT_MARKET_COACH CheckPaymentConfirm GetGamePlanExceptNGWordErrorAlertStr ETUTORIAL_TYPE::ETUTORIAL_TRAINING m_levelCap IsReturnTeamSelect GetTeamSelectAlertTitleString EMenuPickerDateButtonKind::BUTTON_LEFT_DOWN EPlayEnvPlayerCardDispLoad::PLAY_ENV_PLAYER_CARD_DISP_LOAD_LOW EPlayEnvSupportSettingType::PLAY_ENV_SWITCH_TYPE_OFF EAllyPlayEnvCursorNameType::ALLY_PLAY_ENV_CURSOR_NAME_TYPE_USER_NAME EPlayEnvFeintInputType::PLAY_ENV_FEINT_INPUT_TYPE_SMART EPlayEnvContorlStyle EPlayEnvSetti

OFFSET=0xaa5adb TERM=turn
CONTEXT=RemoveCameraModifier ViewPitchMax ClientIgnoreLookInput NewTouchInterface WorldPackageName LevelVisibilities SmoothTargetViewRotationSpeed bEnableClickEvents BlendRadius GetPhysicsLinearVelocity SetOnlyOwnerSee bAlwaysCreatePhysicsState bReturnMaterialOnMove AlwaysLoadOnClient InterpLocationTime OnQuartzCommandEvent__DelegateSignature EQuartzDelegateType EQuartzTimeSignatureQuantization::SixteenthNote BeatType RCCE_Constant EDefaultBackBufferPixelFormat::DBBPF_MAX EEarlyZPass::OpaqueAndMasked bOcclusionCulling bEnableAlphaChannelInPostProcessing DefaultFeatureAntiAliasing bSelectiveBasePassOutputs

OFFSET=0xaa7f72 TERM=turn
CONTEXT=guard_side_set018_pushed_df_act064 new_dribblerun_4_4_067_in gkmovenear_backslantstep_0_3_1_short head_y05_sidle_chest_3_2_f090 head_y07_sidle_chest_3_0_f180 js_run_3_3_000_guard_side_set005_of_lose_act068 autoMove_01_reverse_loop_walkside_turn_1_1_mid autoMove_04_crank45_loop_3_3_mid autoMove_08_ragged45_slant_loop_2_2_FrontBack_mid coach_0_0_000_cross_arms_oop_disappointing_high autoMove_40_circle_run_turn_3_3_mid dm_oop_ballcome_000_side_3_3_run_000 dm_oop_lineback_f045_mid_delay dm_oop_linemove_f090_mid_delay dm_oop_pass_point_000_walk_1_2_run_000 autoMove_01_reverse_loop_front_back_3_3_STEP_m

OFFSET=0xaa8019 TERM=turn
CONTEXT=3_000_guard_side_set005_of_lose_act068 autoMove_01_reverse_loop_walkside_turn_1_1_mid autoMove_04_crank45_loop_3_3_mid autoMove_08_ragged45_slant_loop_2_2_FrontBack_mid coach_0_0_000_cross_arms_oop_disappointing_high autoMove_40_circle_run_turn_3_3_mid dm_oop_ballcome_000_side_3_3_run_000 dm_oop_lineback_f045_mid_delay dm_oop_linemove_f090_mid_delay dm_oop_pass_point_000_walk_1_2_run_000 autoMove_01_reverse_loop_front_back_3_3_STEP_mid_michael autoMove_01_reverse_loop_slant_backslant_1_1_STEP_mid_michael autoMove_03_crank90_loop_2_2_mid_michael autoMove_03_crank90_loop_2_2_STEP_near dml_goal_celeb

OFFSET=0xaa8430 TERM=turn
CONTEXT=ay_Oriul dash_10_side_1_4_f045_dash_Oriul reaction_contact_0_3_090_act071_01 nearDefense_04_BODYTURN_Slant_3_3_f45_f90_f135_reverse_near_gabriel dribble_0_3_f180_y0_sole_act064 dm_oop_pointing_000_walk_1_1_walkback_135 StabilizerCam_corner_turn_2_L dm_oop_pointing_f045_runback_2_2 dm_oop_pointing_f135_walk_1_1 ActualBattle_181002_F100_t02_Gabriel F_ActualBattle_190123_K020_t01_Jua_02_Fcut002 ActualBattle_200127_F025_t02_Ortega enum_dummy24 new_dribblerun_3_0_090_y0_sole_ver03 new_dribblerun_3_3_045_y0_in_ver03 new_dribbleslide180_3_3_slide_180_sole_v3 enum_dummy63 new_dribblerun_3_0_f045_sole_ver1

OFFSET=0xaa89f0 TERM=turn
CONTEXT=ew_dribbleslide045_3_4_f135_y0_out_ver21 new_dribble_0_3_090_in_ver2 LongVersion_171104_F114_t02_Gabriel_02 enum_dummy175 enum_dummy249 autoMove_02_gkmovemid_goto_reverse_stop02_3_3 enum_dummy289 dash_01_CIRCLE_4_4_small_big_act079 dash_04_turn_4_4_165_act079 dash_06_backslant_2_4_parallel_315_act071 dash_06_back_2_4_run_180_act068 dash_06_back_2_4_run_180_act079 dash_06_back_2_4_run_270_act079 dash_07_dash_4_2_side_ball_follow_act080 set_ball_foot_0_0_090_quick set_ball_foot_0_0_180 dm_oop_gk_jog_2_0_Glad_180 enum_dummy337 enum_dummy354 LongVersion_201123_F017_t01_act071_01 enum_dummy356 LongVers

OFFSET=0xaa95c5 TERM=turn
CONTEXT=stant/stadium/demoarea_st018.json DevelopData/common/match/constant/stadium/demoarea_st025.json DevelopData/common/match/constant/stadium/demoarea_st066.json DevelopData/common/match/constant/tutorialConsole/Beginner_Crossing.json L_mic_1C turnStepMove airRegistNormal boundToRotationSpeedMinY nonSpinTopRiseDecRate rollToSpeedMaxRoll isTargetKeepPlayerEnable relayParam assist_over2 many_save freekickDebug pauseRestartMoveTime setupNo p0_speed_average limitFrontX distForGageMax passDistMaxThrough accRateDif180 decMinSpeedR circleDist positionAdjustEnable normalShootGageMid40 adjustFrameSpaceRun manu

OFFSET=0xaa9812 TERM=turn
CONTEXT=meSpaceRun manualPassSpeedAdjust passFrameMargin targetDistMin foot hitFrameBase offsetPos_Dash_Dash offsetPos_Run_Idle offsetPos_Run_Run rateAngleSub trapChapeuAuto adjustAngle_FreeKickSupport attackLevel diffRestartX_Start forceJogDist returnControlSide slideDistMax xposiRateCustom SetStaticPropsParams Animation/ .skl .model cpk_dat/common/demo/fixdemo/goal/table_goal.bin .json fixdemo LoadSublevelUmap skipped_all_initial_pk match_training_pre_load forward ] : State from [ STATE_IDLE AndroidUtil::PesRebootCheck TvHandyCameraMan. team_saopaulo team_nederland cpk_dat/common/match/constant/constan

OFFSET=0xaaaa73 TERM=turn
CONTEXT=_DIALOG_PURCHASE_SUCCESSFUL CmdSetFameFinNewIcon SelectedAgeDisp HistoryRowCount CmdCloseUserCompe PositionTraining_1 AUTHENTIC /Game/Assets/character/Ball/SM_b%03d_Ball.SM_b%03d_Ball waitingFunc AddStadiumDlTaskWait CmdSetSeasonEnter CmdReturnRoom CmdSendJoinRoomRequest CmdUpdateMyclubBaseTeam CmdAddFoul CmdGetMainmenuMatchCreativeInfo CmdGetOnlineAdFileExhibitionESports CmdGetBalanceHistory user_info event_id banner_c_pickup_list received_random_reward phase_start_time score_pk winning_points reward_point special_skill total team_tactics acquisition_date is_completed is_transfer is_skip_match CO

OFFSET=0xaae531 TERM=turn
CONTEXT=invalid regex grammar has been requested. vertical-tab static const char *physx::shdfnd::ReflectionAllocator<unsigned int>::getName() [T = unsigned int] Particle fluid creation failed. Use PxRegisterParticles to register particle module: returned NULL. static const char *physx::shdfnd::ReflectionAllocator<physx::NpPtrTableStorageManager>::getName() [T = physx::NpPtrTableStorageManager] static const char *physx::shdfnd::ReflectionAllocator<physx::PxAggregate *>::getName() [T = physx::PxAggregate *] static const char *physx::shdfnd::ReflectionAllocator<physx::PxConstraint *>::getName() [T = physx::P

OFFSET=0xab1dea TERM=turn
CONTEXT=CmnLinkPitch/CmnLinkPitch_1.CmnLinkPitch_1_C /Game/Assets/menu/common/Views/DetailView/BP_MenuDetailViewEventEulaAgree.BP_MenuDetailViewEventEulaAgree_C CallbackPrivacyEulaAgreeView PauseChoice_9 ScrollBoxCustom_0 _White [%s] Local Check return false. [%s] step:%d -> %d C_Action G:/PES22HC/Dev-600Series/UProject/PesMobile/Source/PesShared/Game/Menu/Common/Views/Announce/UCMenuAnnounceViewBase.h Item_1 /Game/Assets/ui/Data/Widget/General/Views/HintView/HintViewPartsCell.HintViewPartsCell_C Text_Action CP MLPoint Select Emoji Img_PlayerSilhouette CalcCanvasPanelSize AcceptInvitationTest Test Alert

OFFSET=0xab61d6 TERM=turn
CONTEXT=f TextureScaleParameter ExpressionInput PerformanceCapture Filename ERROR_NAME_SIZE_EXCEEDED FPackageLocalizationCultureCache::ConditionalUpdateCache_NoLock DeleteLinkers execVectorConst SessionName ELocalizedTextSourceCategory::Game EAppReturnType::Yes EUnit::Milliseconds EUnit::Years PF_G8 PF_ETC2_RGB RecursiveClassesExclusionSet bDropFrameFormat ZW PackedNormal Vive_Right_Trackpad_Right MixedReality_Left_Thumbstick_Right MixedReality_Right_Thumbstick_Click MixedReality_Right_Trackpad_Click ValveIndex_Left_System_Click ETouchType::Type ETouchIndex::Touch5 EControllerHand::Special_5 FocusRectangl

OFFSET=0xabb397 TERM=turn
CONTEXT=side_set016_pulled_df_act064 gkmovenear_front_sidestep_3_3_000 js_run_3m_3m_000_guard_side_set018_pushed_of_act097 dribblerun_4_4_000_y0_near_out_ver21 stagger_upbody_3_3_090_weakly_v2 autoMove_11_bodyangle_rolling_slow_1_1_mid autoMove_30_turn_move_2_2_CIRCLE_mid autoMove_30_turn_move_3_3_CIRCLE_mid dm_oop_beckon_000_walkback_1_2_runback dm_oop_callback_f135_handup_mid_delay autoMove_01_reverse_loop_front_back_2_2_near autoMove_01_reverse_loop_parallel_turn_3_3_mid_michael autoMove_03_crank90_loop_3_3_STEP_mid_michael autoMove_04_crank45_loop_1_1_mid_michael autoMove_10_bodyangle_keep_circle_bigt

OFFSET=0xabb3bc TERM=turn
CONTEXT=ar_front_sidestep_3_3_000 js_run_3m_3m_000_guard_side_set018_pushed_of_act097 dribblerun_4_4_000_y0_near_out_ver21 stagger_upbody_3_3_090_weakly_v2 autoMove_11_bodyangle_rolling_slow_1_1_mid autoMove_30_turn_move_2_2_CIRCLE_mid autoMove_30_turn_move_3_3_CIRCLE_mid dm_oop_beckon_000_walkback_1_2_runback dm_oop_callback_f135_handup_mid_delay autoMove_01_reverse_loop_front_back_2_2_near autoMove_01_reverse_loop_parallel_turn_3_3_mid_michael autoMove_03_crank90_loop_3_3_STEP_mid_michael autoMove_04_crank45_loop_1_1_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_mid_michael autoMove_10

OFFSET=0xabb471 TERM=turn
CONTEXT=w_1_1_mid autoMove_30_turn_move_2_2_CIRCLE_mid autoMove_30_turn_move_3_3_CIRCLE_mid dm_oop_beckon_000_walkback_1_2_runback dm_oop_callback_f135_handup_mid_delay autoMove_01_reverse_loop_front_back_2_2_near autoMove_01_reverse_loop_parallel_turn_3_3_mid_michael autoMove_03_crank90_loop_3_3_STEP_mid_michael autoMove_04_crank45_loop_1_1_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_mid_michael autoMove_10_bodyangle_keep_circle_smallturn_front_1_1_mid_michael coach_1_1_090_cross_arms_position_up autoMove_40_circle_run_turn_2_2_mid_michael autoMove_40_circle_run_turn_3_3_mid_michael S

OFFSET=0xabb502 TERM=turn
CONTEXT=andup_mid_delay autoMove_01_reverse_loop_front_back_2_2_near autoMove_01_reverse_loop_parallel_turn_3_3_mid_michael autoMove_03_crank90_loop_3_3_STEP_mid_michael autoMove_04_crank45_loop_1_1_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_mid_michael autoMove_10_bodyangle_keep_circle_smallturn_front_1_1_mid_michael coach_1_1_090_cross_arms_position_up autoMove_40_circle_run_turn_2_2_mid_michael autoMove_40_circle_run_turn_3_3_mid_michael Slowerrun_3_0_045 avoidjumpsliding_3_4_000_high_act068_01 avoidjumpsliding_3_4_022_act068_03 autoMove_00_bodyangle_00_135_00_3_3_near_gabriel near

OFFSET=0xabb544 TERM=turn
CONTEXT=ove_01_reverse_loop_parallel_turn_3_3_mid_michael autoMove_03_crank90_loop_3_3_STEP_mid_michael autoMove_04_crank45_loop_1_1_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_mid_michael autoMove_10_bodyangle_keep_circle_smallturn_front_1_1_mid_michael coach_1_1_090_cross_arms_position_up autoMove_40_circle_run_turn_2_2_mid_michael autoMove_40_circle_run_turn_3_3_mid_michael Slowerrun_3_0_045 avoidjumpsliding_3_4_000_high_act068_01 avoidjumpsliding_3_4_022_act068_03 autoMove_00_bodyangle_00_135_00_3_3_near_gabriel nearDefense_04_BODYTURN_Slant_1_1_rightfront_STEP_near_gabriel nearDef

OFFSET=0xabb59b TERM=turn
CONTEXT=_michael autoMove_04_crank45_loop_1_1_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_mid_michael autoMove_10_bodyangle_keep_circle_smallturn_front_1_1_mid_michael coach_1_1_090_cross_arms_position_up autoMove_40_circle_run_turn_2_2_mid_michael autoMove_40_circle_run_turn_3_3_mid_michael Slowerrun_3_0_045 avoidjumpsliding_3_4_000_high_act068_01 avoidjumpsliding_3_4_022_act068_03 autoMove_00_bodyangle_00_135_00_3_3_near_gabriel nearDefense_04_BODYTURN_Slant_1_1_rightfront_STEP_near_gabriel nearDefense_04_BODYTURN_Slant_1_1_rightside_STEP_near_gabriel gkblock_lie_s04_0_0_y04_090 near

OFFSET=0xabb5c7 TERM=turn
CONTEXT=chael autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_mid_michael autoMove_10_bodyangle_keep_circle_smallturn_front_1_1_mid_michael coach_1_1_090_cross_arms_position_up autoMove_40_circle_run_turn_2_2_mid_michael autoMove_40_circle_run_turn_3_3_mid_michael Slowerrun_3_0_045 avoidjumpsliding_3_4_000_high_act068_01 avoidjumpsliding_3_4_022_act068_03 autoMove_00_bodyangle_00_135_00_3_3_near_gabriel nearDefense_04_BODYTURN_Slant_1_1_rightfront_STEP_near_gabriel nearDefense_04_BODYTURN_Slant_1_1_rightside_STEP_near_gabriel gkblock_lie_s04_0_0_y04_090 nearDribble_04_1_dribble_burst_1_4_135_y0_oriul 

OFFSET=0xabbdc3 TERM=turn
CONTEXT=_200127_F004_t01_Takayama enum_dummy216 enum_dummy226 enum_dummy244 enum_dummy251 autoMove_02_gkmovenear_goto_reverse_stop02_3_3 enum_dummy287 enum_dummy288 autoMove_06_zigzag180_side_loop_1_2_3_warning_act079 autoMove_40_circle_short_side_turn_1_1_bodyangle_keep_act079 dash_03_loop_4_2_4_090_act068 dash_06_back_2_4_run_act079 dash_07_dash_4_1_walkslant_ball_follow_act071 pull_ball_foot_3_0_090_kick pull_ball_foot_3_0_f090_kick fall_upbody_3_0_090_interrupt_lose_act071 enum_dummy291 dm_oop_gk_jog_2_0_idle_walkGuts_180 dm_oop_gk_walk_0_1_idle_walkGuts_090 dm_oop_appeal_3_3_000_at135_act071 dm_oop_p

OFFSET=0xabc1ce TERM=turn
CONTEXT=_ChageAngle03_1_1 autoMove_00_gkmovenear_step_ChageAngle03_3_3 NEARKEEPER_04_02_gkmovenear_1_1_BODYTURN_SLANT NEARKEEPER_04_03_gkmovenear_3_3_BODYTURN_SLANT enum_dummy541 enum_dummy567 enum_dummy637 block_3_0_y00_f090_act071 gkmovenear_stopturn_2_0_v2 Project.hkx isRandomHandL base_d_end_banzai_hoe base_d_ent_warai base_g_catchs base_kuisibari_hard bitter_brwin_smirk_eyhc dml_neut_brwtrb_talk gk_brwup_puff_lith_fast neut_brwin_r neut_puck_mid neut_sbreth_around pose_angry_talk_S_02 pose_neut_talk_03 pose_sorrow_dejection_M_03 pose_sorrow_displeasure_04 smile_shout_M_01 smil_brwnit_grit_eyhc_hard s

OFFSET=0xabc6d6 TERM=turn
CONTEXT=ation Failed to load CRL file (path? access rights?, format?) Bad IPv6 address Protocol "%s" %s%s all_proxy Connecting to hostname: %s %u/%d/%s Failed to resolve %s '%s' with timeout after %ld ms EEEE AAAAGAIN file://%s%s%s multi BIO_new return NULL, OpenSSL error %s CAfile: %s Change cipher spec CERT verify Expire date %02x: %s(%s) ipv6 address PING ws_send_raw_blocking() partial, %zu left to send constraints endurancePower heightMin ag PLAYER_%s%02d DevelopData/common/match/constant/ballPerson/ball_person_st015.json DevelopData/common/match/constant/ballPerson/ball_person_st045.json DevelopData

OFFSET=0xabd14a TERM=turn
CONTEXT= false [TrapBetween] ballDist = %.2f ballDist = %.2f demo_miss_thumbsup_0_1 demo_coop_inspire_2 demo_pfm_cornerF_kick_l demo_pfm_jumpunderguts_3_3_l demo_goal_recorder_loop goalkick_instep_r puntkick_side_0_0_fast2 linesman_4_4 linesman_turn_4_4 seamless_run_throw_3_0 seamless_catch_turn_setup_0_0_y6 blockfront_0_0_y00_shoot blockfront_0_0_y02_shoot_reaction_v3 blockfront_2_0_y01 fall_lowbody_2_0_v4_l fall_lowbody_2_0_v4_r fall_lowbody_4_0_v2_r stagger_ballhit_3_3 stagger_ballhit_belly_0_0_quickly gkfall_catch_0_0 goalturn_dash_2_4 goalturn_crawl_2_4 demo_move_3_1_045_step demo_move_3_0_side de

OFFSET=0xabd179 TERM=turn
CONTEXT== %.2f demo_miss_thumbsup_0_1 demo_coop_inspire_2 demo_pfm_cornerF_kick_l demo_pfm_jumpunderguts_3_3_l demo_goal_recorder_loop goalkick_instep_r puntkick_side_0_0_fast2 linesman_4_4 linesman_turn_4_4 seamless_run_throw_3_0 seamless_catch_turn_setup_0_0_y6 blockfront_0_0_y00_shoot blockfront_0_0_y02_shoot_reaction_v3 blockfront_2_0_y01 fall_lowbody_2_0_v4_l fall_lowbody_2_0_v4_r fall_lowbody_4_0_v2_r stagger_ballhit_3_3 stagger_ballhit_belly_0_0_quickly gkfall_catch_0_0 goalturn_dash_2_4 goalturn_crawl_2_4 demo_move_3_1_045_step demo_move_3_0_side demo_gk_glad_6 trapstep_000_0_3_y0_in demo_gk_ang

OFFSET=0xabd269 TERM=turn
CONTEXT=turn_setup_0_0_y6 blockfront_0_0_y00_shoot blockfront_0_0_y02_shoot_reaction_v3 blockfront_2_0_y01 fall_lowbody_2_0_v4_l fall_lowbody_2_0_v4_r fall_lowbody_4_0_v2_r stagger_ballhit_3_3 stagger_ballhit_belly_0_0_quickly gkfall_catch_0_0 goalturn_dash_2_4 goalturn_crawl_2_4 demo_move_3_1_045_step demo_move_3_0_side demo_gk_glad_6 trapstep_000_0_3_y0_in demo_gk_angry_9 demo_angry_hurry_2 demo_miss_3_1_bendback_000_2 demo_gk_miss_fallside_5 demo_appeal_0_1_at045_4_pat_2 demo_appeal_3_1_135 dodge_net_0_3 doubletouch_scissors_3_3_l inout_0_3_l roulettesingle_0_3_r shakefoottwice_0_0_l kick_mid_3_0_infro

OFFSET=0xabd27b TERM=turn
CONTEXT=blockfront_0_0_y00_shoot blockfront_0_0_y02_shoot_reaction_v3 blockfront_2_0_y01 fall_lowbody_2_0_v4_l fall_lowbody_2_0_v4_r fall_lowbody_4_0_v2_r stagger_ballhit_3_3 stagger_ballhit_belly_0_0_quickly gkfall_catch_0_0 goalturn_dash_2_4 goalturn_crawl_2_4 demo_move_3_1_045_step demo_move_3_0_side demo_gk_glad_6 trapstep_000_0_3_y0_in demo_gk_angry_9 demo_angry_hurry_2 demo_miss_3_1_bendback_000_2 demo_gk_miss_fallside_5 demo_appeal_0_1_at045_4_pat_2 demo_appeal_3_1_135 dodge_net_0_3 doubletouch_scissors_3_3_l inout_0_3_l roulettesingle_0_3_r shakefoottwice_0_0_l kick_mid_3_0_infront_y0_lob slidesci

OFFSET=0xabd7a7 TERM=turn
CONTEXT=rapside_l_0_3_y4_instep trapside_l_3_3_y4_in_near trapside_l_3_3_y4_breast_bound trapside_l_2_3_y2_in trapside_r_3_3_y4_out trapside_r_4_4_y0_out_far tackle_0_0_mid_parallel gkrise_sidewaysAction1_r demo_angry_3_1_046 demo_gk_cheer_9 springturn_0_3_r tapfake_3_3_l blendStart=%d animeFrame=%d [Command] ControlMode [%s](high ball & exist other follow player%d) [Command] ControlMode [%s](fix or semiFix cursor & gk & team offence) [Command] ControlMode [%s] (setplay & main kicker) PlayerVsPlayer Atari_HumanLeg_Hit_01 MatchMobListenerBase Steward TypeNum RSB stop2 outPos.x=%f outPos.z=%f line=%d 

OFFSET=0xabf4df TERM=turn
CONTEXT=ce error:not found healthCheckConfig field:retryableStatusCodes error:Duplicate entry HealthCheckClient %p: setting state=%s reason=%s HealthCheckClient %p: shutting down error == GRPC_ERROR_NONE client-channel chand=%p calld=%p: LB pick returned %s (subchannel=%p, error=%s) chand=%p: resolver returned invalid service config. Using default service config provided by client API. HTTP proxy returned response code %d HTTP:POST:%s:%s G:\PES22HC\Dev-600Series\Source\Shared\basic\ext\grpc\grpc\src\core\ext\transport\chttp2\client\secure\secure_channel_create.cc Failed to create channel args during subch

OFFSET=0xabf518 TERM=turn
CONTEXT=sCodes error:Duplicate entry HealthCheckClient %p: setting state=%s reason=%s HealthCheckClient %p: shutting down error == GRPC_ERROR_NONE client-channel chand=%p calld=%p: LB pick returned %s (subchannel=%p, error=%s) chand=%p: resolver returned invalid service config. Using default service config provided by client API. HTTP proxy returned response code %d HTTP:POST:%s:%s G:\PES22HC\Dev-600Series\Source\Shared\basic\ext\grpc\grpc\src\core\ext\transport\chttp2\client\secure\secure_channel_create.cc Failed to create channel args during subchannel creation. self->connecting_ ads_calld->call_ != nul

OFFSET=0xabf579 TERM=turn
CONTEXT=p: shutting down error == GRPC_ERROR_NONE client-channel chand=%p calld=%p: LB pick returned %s (subchannel=%p, error=%s) chand=%p: resolver returned invalid service config. Using default service config provided by client API. HTTP proxy returned response code %d HTTP:POST:%s:%s G:\PES22HC\Dev-600Series\Source\Shared\basic\ext\grpc\grpc\src\core\ext\transport\chttp2\client\secure\secure_channel_create.cc Failed to create channel args during subchannel creation. self->connecting_ ads_calld->call_ != nullptr [xds_client %p] xds channel in state TRANSIENT_FAILURE grpc_google_default_credentials_creat

OFFSET=0xac8ac7 TERM=turn
CONTEXT=KHR(Device.GetPhysicalHandle(), Surface, &NumFormats, nullptr) PresentResult scaling_cur_freq (Landroid/app/Activity;)V 1.2.5 LinearColor ExecuteUbergraph NetworkGUID DestinationObject execBindDelegate COND_None COND_AutonomousOnly EAppReturnType::YesAll EUnit::Micrometers PF_A32B32G32R32F PF_G32R32F PF_R16F PF_BC5 PF_ETC1 PF_NV12 EAxis::None EAxis::X InVal Center C_Cedille Tilt Vive_Left_Trackpad_Y OculusTouch_Left_Thumbstick_Up OculusTouch_Right_A_Click OculusTouch_Right_Thumbstick_Click ValveIndex_Left_Thumbstick_Click ETouchType::Stationary ETouchIndex::Touch8 EControllerHand::Special_7 getC

OFFSET=0xaca266 TERM=turn
CONTEXT=vieExtension ResY G:/UE4.26_eFB/Base/Engine/Source/Runtime/Engine/Classes/Animation/AnimNode_CustomProperty.h InPose EventWait/Cloth Physics G:/UE4.26_eFB/Base/Engine/Source/Runtime/Engine/Private/Rendering/StreamableTextureResource.cpp return Result; ResizeArrayNegativeWarning ReplicateActorTimeMS CompositeEditorPrimitives PhysicalMaterialMasks Tessellation HitProxies ShadowFrustums ScreenSpaceAO VisualizeSenses LODs EquirectLayer SetActorHiddenInGame SetLifeSpan Loudness ReceiveRadialDamage bAlwaysRelevant ParentComponent AlphaBlend PositionBetweenMarkers bForceBelowThreshold bUseMultiThreade

OFFSET=0xacdecf TERM=turn
CONTEXT=o_reverse_3_3m_act097 fk_idle_ronaldinho_2 gkmoveSeriesA_Back_1_1_Reverse gkmovenear_backstep_0_3_1_short gkprejump_0_0_near_min3 js_slant_2_2_loop_guard_back_sub autoMove_03_crank90_loop_3_3_STEP_mid autoMove_10_bodyangle_keep_circle_smallturn_front_1_1_STEP_mid dm_oop_ballcome_000_walkback_1_2_runback dm_oop_ballcome_f090_side_2_2_runback_090 dm_oop_beckon_f180_side_2_2_000 dm_oop_linekeep_f135_mid_delay_v2 dm_oop_pass_point_000_run_3_4_000 autoMove_00_bodyangle_00_90_180_00_2_2_STEP_mid_michael Ballboy_standup_y0_y3 autoMove_04_crank45_loop_2_2_STEP_mid_michael autoMove_07_ragged45_front_loop_3

OFFSET=0xace074 TERM=turn
CONTEXT=ass_point_000_run_3_4_000 autoMove_00_bodyangle_00_90_180_00_2_2_STEP_mid_michael Ballboy_standup_y0_y3 autoMove_04_crank45_loop_2_2_STEP_mid_michael autoMove_07_ragged45_front_loop_3_3_STEP_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_STEP_near autoMove_03_crank90_loop_1_1_STEP_near_gabriel autoMove_06_zigzag135_side_loop_1_1_STEP_near_gabriel dm_goal_extra_loop_0003 dash_04_turn_4_4_045_CIRCLE_Oriul dash_09_idle_0_4_180_dash_Oriul dash_10_walk_1_4_180_dash_Oriul nearDefense_04_BODYTURN_Slant_1_1_f45_90_f135_reverse_near_gabriel nearDefense_04_BODYTURN_Slant_2_2_rightside_STEP_

OFFSET=0xace112 TERM=turn
CONTEXT=_07_ragged45_front_loop_3_3_STEP_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_STEP_near autoMove_03_crank90_loop_1_1_STEP_near_gabriel autoMove_06_zigzag135_side_loop_1_1_STEP_near_gabriel dm_goal_extra_loop_0003 dash_04_turn_4_4_045_CIRCLE_Oriul dash_09_idle_0_4_180_dash_Oriul dash_10_walk_1_4_180_dash_Oriul nearDefense_04_BODYTURN_Slant_1_1_f45_90_f135_reverse_near_gabriel nearDefense_04_BODYTURN_Slant_2_2_rightside_STEP_near_gabriel gkmovehigh_idle_0_0_180_ball gkcatchslideback_f01_3_0_y02_135 nearDribble_01_1_dribble_bodyfake_0_0_to_3_3_000_y0_gabriel nearDribble_04_1_dribbl

OFFSET=0xace8d9 TERM=turn
CONTEXT=w_walk_1_1 new_walk_1_1_walkback_180_warning enum_dummy145 LongVersion_180928_F004_t02_Gabriel_01 enum_dummy166 LongVersion_200127_F001_t01_Gabriel LongVersion_200127_F002_t01_Ortega LongVersion_200127_F003_t01_Ortega enum_dummy202 dash_04_turn_4_4_parallel_135_act079 dash_04_turn_4_4_parallel_180_act079 pull_ball_foot_3_0_000_kick ActualBattle_201124_F035_t01_act068_05 enum_dummy297 dm_oop_angry_3_3_090_act071_03 dm_oop_appeal_3_3_090_at135_act064 dm_oop_appeal_3_3_180_at135_act064 dm_oop_droop_1_3_090_act071_02 dm_oop_droop_3_3_180_act064_02 dm_oop_praise_1_3_090_at090_act071 dm_oop_praise_1_3_1

OFFSET=0xace8fe TERM=turn
CONTEXT=warning enum_dummy145 LongVersion_180928_F004_t02_Gabriel_01 enum_dummy166 LongVersion_200127_F001_t01_Gabriel LongVersion_200127_F002_t01_Ortega LongVersion_200127_F003_t01_Ortega enum_dummy202 dash_04_turn_4_4_parallel_135_act079 dash_04_turn_4_4_parallel_180_act079 pull_ball_foot_3_0_000_kick ActualBattle_201124_F035_t01_act068_05 enum_dummy297 dm_oop_angry_3_3_090_act071_03 dm_oop_appeal_3_3_090_at135_act064 dm_oop_appeal_3_3_180_at135_act064 dm_oop_droop_1_3_090_act071_02 dm_oop_droop_3_3_180_act064_02 dm_oop_praise_1_3_090_at090_act071 dm_oop_praise_1_3_180_at090_act071 LongVersion_201123_F0

OFFSET=0xacf841 TERM=turn
CONTEXT=ancel throw_under_3_0_near seamless_catch_3_3_y7 seamless_carry_ball_move_0_3 blockfront_0_0_y04 blockfront_3_0_y00 blockside_0_0_y00 fall_lowbody_2_0_sliding_high_l fall_lowbody_3_0_v4_l fall_lowbody_4_0_v5_r stagger_ballhit_belly_3_3 goalturn_comeon_2_4 demo_gk_glad_14 demo_miss_3_1_droop_045 demo_miss_3_1_face_090 demo_miss_0_0_handOnKnee demo_miss_1_1_side demo_miss_facedown_135_3 demo_droop_hurry_7 demo_droop_hurry_14 demo_appeal_2_1_045 demo_appeal_hurry_4 demo_praise_0_1_at045_1 demo_gk_angry_12 demo_praise_hurry_7 TimeUp_1_1_Grad_0_5 HalfEnd_0_1_Droop_0_1 dodge_ball_2_0_slide_back_mid body

OFFSET=0xad202a TERM=turn
CONTEXT=ers\client_channel\resolver_registry.cc Connect failed: %s invalid ipv4 address: '%s' grpc.subchannel_pool health check call failed; will retry after backoff HealthCheckClient %p: restarting health check call completed chand=%p: resolver returned invalid service config. Continuing to use previous service config. run_poller !grpclb_policy->shutting_down_ [cdslb %p] received CDS update from xds client G:\PES22HC\Dev-600Series\Source\Shared\basic\ext\grpc\grpc\src\core\ext\filters\client_channel\xds\xds_channel_secure.cc certificate_type Could not add root certificate to ssl context. Corruption detec

OFFSET=0xada32b TERM=turn
CONTEXT=ion GetActionStr GetScrollChoiceKind AcceptSideLeaderSettingFlag AcceptChangeStrikeArenaInfoFlag UserIdList1 ELayoutMatchMainMenuLobbyChoiceIcon SimpleRecords isInvited ELobbyRoomMainChoiceType::SQUAD_EDIT LobbyRoomMainChoiceInfo FinishedReturnFromMatch ELobbyRoomMatchSettingsItem ELobbySideSelectSideAnime::MoveAwayToHome SetLoginBonusKind ELoginBonusPresentType::PRESENT_TYPE_DRAFT EMenuMailboxCommandResult EMenuMailboxReceiveAlertType::RECEIVE_ALERT_SINGLE EMenuMailboxReceiveResult::RECEIVE_RESULT_DETECT_REFUND EMenuMailboxReceiveResult::RECEIVE_RESULT_FAIL_UNIQUE EMenuMailboxReceiveResult OnRele

OFFSET=0xae0b11 TERM=turn
CONTEXT=op_1_1_STEP_mid_michael coach_1_1_090_cross_arms_oop_protest Slowerrun_3_0_135 autoMove_01_reverse_loop_side_1_1_STEP_near_gabriel autoMove_04_crank45_loop_2_2_STEP_near_gabriel autoMove_05_zigzag135_front_loop_3_3_near_gabriel autoMove_30_turn_move_2_2_CRANK_near_gabriel autoMove_00_bodyangle_00_135_00_2_2_STEP_near_gabriel autoMove_00_bodyangle_00_90_00_1_1_STEP_near_gabriel autoMove_00_dribble_bodyangle_00_135_00_2_2_STEP_near_gabriel autoMove_32_dribble_go_to_3_3_near_gabriel ballTouch_04_4_dribble_player_move_0_3_000_and_045_and_f045_y0_gabriel moveAdjust_05_Back_3_3_gabriel gkcatchslideback_

OFFSET=0xae0df9 TERM=turn
CONTEXT=le_04_1_dribble_burst_0_4_000_y0_take1_oriul reaction_contact_3_4_090_act071_01 dribblerun_arc_3m_3m_045_y2_in_act064 dribblerun_arc_3m_3m_f045_y2_out_act064 idle_0_3_run_135_push_aside js_parallel_crash_000_set01_3_3_225_df_act064 dash_05_turn_4_3_135_CRANK pk_enclose_kamae gkseeoff_side_near_react_0_1_y11 dml_goal_celebrate_0063 dml_goal_celebrate_0135 dml_goal_celebrate_0141 dm_oop_pass_point_f090_run_3_4_f090 dm_oop_pointing_f045_mid_delayside_2_2 dm_oop_pointing_f045_mid_delay_0_0 ActualBattle_181002_F100_t06_Gabriel ActualBattle_191008_FZ007_t10_Gabriel F_ActualBattle_191005_F006_t01_Gabriel

OFFSET=0xae1b2d TERM=turn
CONTEXT=n abort upload after having sent %ld bytes client_read(len=%zu) -> %d, nread=%zu, eos=%d client read function EOF fail, only %ld/%ld of needed bytes read cw_out, PAUSE requested by client Failure writing output to destination, passed %zu returned %zd SOCKS5: connecting to HTTP proxy %s port %d User was rejected by the SOCKS5 server (%d %d). SOCKS5 connect request address Quote command returned error LDAP: cannot bind Can not set SSL crypto engine as default Problem with the local SSL certificate Unrecognized or bad HTTP Content or Transfer-Encoding Invalid easy handle No scheme part in the URL Bad

OFFSET=0xae1bc3 TERM=turn
CONTEXT=ead cw_out, PAUSE requested by client Failure writing output to destination, passed %zu returned %zd SOCKS5: connecting to HTTP proxy %s port %d User was rejected by the SOCKS5 server (%d %d). SOCKS5 connect request address Quote command returned error LDAP: cannot bind Can not set SSL crypto engine as default Problem with the local SSL certificate Unrecognized or bad HTTP Content or Transfer-Encoding Invalid easy handle No scheme part in the URL Bad login part CURL_SSL_BACKEND SSL certificate verify result: %s (%ld), continuing anyway. TLSv1.1 Upgrade: buffered MultiShoulderConstraint OUTPUT DEM

OFFSET=0xae238e TERM=turn
CONTEXT=dle_0_1_sidestep dm_oop_ballcome_000_idle_0_2_side dm_oop_facedown_0_0_idle_protest_hard goalkick_instruction_1_r puntkick_front_0_0_hard throw_over_0_0_nearline_cancel throw_under_0_0_fast throw_over_3_0_hard judge_point_to_3_low linesman_turn_3_3_run linesman_turn_3_3 trapback_0_3_y0_in_back_f seamless_pull_ball_foot_kick_3_0 blockfront_0_0_y04_shoot goalkick_seamless_idle_l fall_air_upbody_3_0 fall_lowbody_3_0_v3_r fall_lowbody_4_0_v5_l fall_upbody_0_0_facecover stagger_air_upbody_0_0 goalturn_facedown demo_move_0_1_045_head demo_gk_glad_19 demo_angry_1_1_side demo_gk_angry_turn_135_1 demo_gk_a

OFFSET=0xae23a4 TERM=turn
CONTEXT=p_ballcome_000_idle_0_2_side dm_oop_facedown_0_0_idle_protest_hard goalkick_instruction_1_r puntkick_front_0_0_hard throw_over_0_0_nearline_cancel throw_under_0_0_fast throw_over_3_0_hard judge_point_to_3_low linesman_turn_3_3_run linesman_turn_3_3 trapback_0_3_y0_in_back_f seamless_pull_ball_foot_kick_3_0 blockfront_0_0_y04_shoot goalkick_seamless_idle_l fall_air_upbody_3_0 fall_lowbody_3_0_v3_r fall_lowbody_4_0_v5_l fall_upbody_0_0_facecover stagger_air_upbody_0_0 goalturn_facedown demo_move_0_1_045_head demo_gk_glad_19 demo_angry_1_1_side demo_gk_angry_turn_135_1 demo_gk_angry_lie_5 demo_angry_

OFFSET=0xae248f TERM=turn
CONTEXT=sman_turn_3_3 trapback_0_3_y0_in_back_f seamless_pull_ball_foot_kick_3_0 blockfront_0_0_y04_shoot goalkick_seamless_idle_l fall_air_upbody_3_0 fall_lowbody_3_0_v3_r fall_lowbody_4_0_v5_l fall_upbody_0_0_facecover stagger_air_upbody_0_0 goalturn_facedown demo_move_0_1_045_head demo_gk_glad_19 demo_angry_1_1_side demo_gk_angry_turn_135_1 demo_gk_angry_lie_5 demo_angry_hurry_5 demo_angry_hurry_13 demo_miss_0_2_bendback_135 demo_miss_3_1_bendback_000 demo_miss_3_1_head_045 demo_miss_3_0_faceup demo_sorry_4_1_lineout_135 TimeUp_0_0_Grad_2_1 TimeUp_1_1_Grad_0_4 dodge_human_slide_rapid_down_4_4 dodge_hum

OFFSET=0xae24e6 TERM=turn
CONTEXT=_y04_shoot goalkick_seamless_idle_l fall_air_upbody_3_0 fall_lowbody_3_0_v3_r fall_lowbody_4_0_v5_l fall_upbody_0_0_facecover stagger_air_upbody_0_0 goalturn_facedown demo_move_0_1_045_head demo_gk_glad_19 demo_angry_1_1_side demo_gk_angry_turn_135_1 demo_gk_angry_lie_5 demo_angry_hurry_5 demo_angry_hurry_13 demo_miss_0_2_bendback_135 demo_miss_3_1_bendback_000 demo_miss_3_1_head_045 demo_miss_3_0_faceup demo_sorry_4_1_lineout_135 TimeUp_0_0_Grad_2_1 TimeUp_1_1_Grad_0_4 dodge_human_slide_rapid_down_4_4 dodge_human_slide_rapid_up_3_3 dodge_ball_2_0_slide_back_low elastico_3_3_l kickfeint_3_3_y0_r k

OFFSET=0xae62d7 TERM=turn
CONTEXT=rt protocol version heartbeat request already pending unknown pkey type unknown protocol unsupported status type , arg= no_ssl3 max_protocol EncryptThenMac SSLv3/TLS write finished TWSKU Exhibition/ExhibiFlowEnd Online/Lobby/ProcLobbyRoomReturnFromMatch Online/EvCompe/ProcEvCompeEventSelect Online/EvCompe/EventCompe/ProcessPostGamePlan Online/EvCompe/MlEvent/Match/ProcMlEventPreScheduleAfterMatch postOnlineObserveMatch match_replay path_to_glory_start SoundReadyObserber /Game/Assets/bg/Stadium/st095/Levels/st095_menu_all.st095_menu_all TaskLobbySetSingleRoom ml_event teamselect entrylobby NEXTLB 

OFFSET=0xae7f03 TERM=turn
CONTEXT=p %d sn-hant Ignoring invalid time value unexpected end of LZ stream ICC profile tag start not a multiple of 4 profile ' png_image_begin_read_from_stdio: invalid argument conflicting calls to set alpha mode and background png_do_quantize returned rowbytes=0 bad compression method Insufficient memory for pCAL purpose invalid location in png_set_unknown_chunks no rows for png_write_image to write png_image_write_to_file: incorrect PNG_IMAGE_VERSION png_image_write_: out of memory Unrecognized unit type for oFFs chunk deflateEnd failed (ignored) mPipelineModeAutoMode Failed to get Build.VERSION class

OFFSET=0xaea22c TERM=turn
CONTEXT=pt/CriWareVIP OnRep_SourceFlipbook UpdateInstanceColor BodySetup TerrainColor EndCap DrawOrder LayerHeight GetTileMapColor bCreateLayer TileX TileY ESpritePivotMode::Bottom_Center ESpriteShapeType::Polygon InActor BlendSignificanceValue bReturnToPreviousState TrackRenderData PlayReversedFromEnd ElapsedTime ImgMedia ConnectToEndpoints RemoveActorFromLayer AndroidPermissionDynamicDelegate__DelegateSignature bUseGpu ETextureRotationDirection::Right /Script/AssetTags GetCollectionsContainingAsset NumSides RiseRate GetCurrentGear bNewGearDown SteeringInputRate (Landroid/content/Context;)Z IsNotificatio

OFFSET=0xaf30f5 TERM=turn
CONTEXT=ck_3_1_walk_head_180 dm_oop_gk_lie_0_1_walkangry dm_miss_idle_0_1_walk_droop_045_2 dm_miss_jog_2_1_walk_openArm_045 dm_miss_jog_2_1_walk_openArm_135 dm_miss_runHip_3_1_walk_090 dm_miss_run_3_1_walk_bendBack_135 dm_move_runStop_3_1_walk_180_turn dm_oop_allfours_0_0_idle_protest_090 dm_oop_gk_idle_0_0_idle_seeOff_000 dm_oop_idle_0_1_walk_handclap_at045 dm_oop_idle_0_1_walk_handclap_at135 dm_oop_touchHigh_idle_0_0_idle_f045_sub dm_pfm_running_3_3_jumpUppercut dribblerun_3_0_180_y0_far_sole_ver12 dribblerun_4_4_022_y4_thigh_ver13 dribblerun_4_4_022_y5_near_thigh_ver01 gklying_ex_faceuphip_0_0_000 gkly

OFFSET=0xaf3f8d TERM=turn
CONTEXT=90_shed dm_oop_gk_lie_0_1_walkCheer_02 coach_0_0_000_normal_oop_protest dm_oop_ballcome_handup_one_far_000_idle autoMove_06_zigzag135_side_loop_1_1_STEP_mid_michael new_dribblerun_4_4_067_in_far autoMove_10_dribble_bodyangle_keep_circle_bigturn_front_2_2_mid_gabriel gkgoalkick_Quick_long_0_0_000_right avoidjumpsliding_3_4_000_act068_01 autoMove_02_reverse_stop_front_back_2_2_STEP_near_gabriel autoMove_07_ragged45_front_loop_1_1_STEP_near_gabriel autoMove_08_dribble_ragged45_slant_loop_2_2_STEP_near_gabriel autoMove_32_dribble_go_to_1_1_near_gabriel autoMove_35_TURNCANCEL_long_Front_3_3_f135_f180_n

OFFSET=0xaf5863 TERM=turn
CONTEXT=ine_cancel throw_under_3_0_near_hard linesman_offside_mid_fromflagup reboundstep_0_4_l blockside_3_0_y02_fishdive fall_lowbody_0_0_sliding_r fall_lowbody_3_0_v2_r fall_lowbody_3_0_sliding_high_l fall_upbody_4_0_v2 stagger_lowbody_0_0_r goalturn_handup_2_4 demo_move_3_1_135_look demo_move_tired_000 demo_gk_glad_lie_7 demo_angroy_allfours demo_angry_hurry_19 demo_gk_miss_2 demo_appeal_0_1_at045_1 demo_appeal_1_1_000 demo_appeal_2_1_135 demo_appeal_nofoul_135 demo_praise_hurry_14 TimeUp_1_1_Grad_0_1 TimeUp_0_0_Droop_2_0 HalfEnd_3_1_Droop_0_1 dodge_human_decelerate_4_3 doubletouch_ballroll_stepover_3_

OFFSET=0xaf8cb3 TERM=turn
CONTEXT=adsi des-cbc emailAddress dsaEncryption-old RC2-40-CBC MD5-SHA1 md5-sha1 Policy Qualifier CPS SMIME-CAPS pbeWithSHA1AndDES-CBC id-smime-aa-ets-signerLocation id-smime-alg-ESDH ac-targeting sbgp-ipAddrBlock id-regInfo-utf8Pairs id-cmc-dataReturn id-cmc-decryptedPOP id-cmc-lraPOPWitness id-qcs-pkixQCSyntax-v1 rsaSignature associatedDomain associatedName personalTitle friendlyCountryName subtreeMaximumQuality MIME MHS setct-PCertResTBS setct-CredRevResTBE International Organizations AES-128-CFB8 DES-CFB8 DES-EDE3-CFB8 sha384WithRSAEncryption c2pnb304w1 secp256k1 wap-wsg-idm-ecid-wtls4 wap-wsg-idm-eci

OFFSET=0xaf9e2b TERM=turn
CONTEXT=led The expression contained an invalid character class name. less-than-sign static const char *physx::shdfnd::ReflectionAllocator<physx::shdfnd::MutexImpl>::getName() [T = physx::shdfnd::MutexImpl] Particle system initialization failed: returned NULL. G:\RenderPlat\Engine\Source\ThirdParty\PhysX3\PhysX_3.4\Source\compiler\cmake\android\..\..\..\PhysX\src/NpActorTemplate.h G:\RenderPlat\Engine\Source\ThirdParty\PhysX3\PhysX_3.4\Source\PhysX\src\NpRigidDynamic.cpp NpScene.completion static const char *physx::shdfnd::ReflectionAllocator<physx::Scb::RemovedShape>::getName() [T = physx::Scb::RemovedSh

OFFSET=0xafe3af TERM=turn
CONTEXT=rcelonaBuildCredit %s RenderTransform SBackgroundBlurCustom CreateBGWidgetByZOrder [AWindowManager::HasEndingChildren] m_childWindowsEnding size[%d] [Vip] RequestVipReleaseToVipController, UPesStreamingMovieWidget::CloseImpl FrameInReturnEnd OnSoftwareResetAfter teamID EAssetResidentType::UserWidget_Match EAssetResidentType::UserWidget_MatchCommon EAssetResidentType::UserWidget_UIFlow EAudiSetupType::SETUP_TYPE_HEAVYWEIGHT_0 EAudiCommonType::Type_Away ComponentID SetupInstance ClipDatas KindVariation CaptureVariationNum MufflerPartsParams_Key LimitX OnReadyCharacter__DelegateSignature ResetP

OFFSET=0xaff294 TERM=turn
CONTEXT=ecide isAllowBlankText openFrom m_AnnounceViewFadeCallBackEvent OnSwitchAnimationFinished ECampaignPassTaskListSegment::Achievement CallbackClosedAlertCampaignPassGetPoint DispSuccessfulDialog GetScrollBoxForDebugCapture newsCategory m_onReturnClose CallbackWebView FMenuEvCompeCompeEventMatchState::UNFINISHED_MATCH m_isImpossibleToJoin m_fStrDispCpuLevel OnOpenUpdateItemAlert EFriendListChoiceSwitchType::FriendListChoiceSwitchTypeNext CallbackFinishedAction EVENT_BONUS_ABILITY ViewCallBackCloseEvent EMenuMenuIconAlertOneBtnIconKind::Icon_AllItem OnCloseRoomSettingView CmnMatchLabelAlignment m_item

OFFSET=0xafffa2 TERM=turn
CONTEXT=ist ELobbyRoomActionKind::SideLeader AcceptOpenFriendListInvitation OpenMatchHistory IsForPadEvent RequestMenuDelegates ELayoutMatchMainMenuCoopUserRequest::Random UpdatePageText OwnerStr DailyPointHeadlineStr HeadlineStrEventGameLevel IsReturningFromMatch ELobbyRoomMatchSettingsItem::PK ELobbySideSelectSideAnime::MoveHomeToAway StartInterruptionMode ELoginBonusPresentType::PRESENT_TYPE_COIN EMenuMailboxReceiveAlertType GetNewsInfoList IsLoadErrorAdMobReward SelectAdvertisingReward SetCmdGetPresent breakdownPresentId m_topWidget OnPressedCameraTargetMinusButton OnPressedCameraTypeMinusButton OnPre

OFFSET=0xb0329c TERM=turn
CONTEXT=stroyActor K2_SetActorTransform SetActorScale3D SetReplicateMovement InputAxisKey OverlappingActors IsComponentTickEnabled EAnimGroupRole::CanBeLeader EPreviewAnimationBlueprintApplicationMethod ScaleErrorSourceRatio ABPT_MAX EMontagePlayReturnType::MontageLength IsPlayingSlotAnimation BranchingPoints BranchingPointMarkers EPinHidingMode::PinShownByDefault PostCopyOperation AnimNode_CustomProperty EInertializationSpace::WorldRotation PostEvaluateAnimEvent__DelegateSignature EAnimInterpolationType::Linear EAnimInterpolationType::Step BCS_MAX bConvertedFromBranchingPoint StartupArguments IgnoreObjec

OFFSET=0xb06c18 TERM=turn
CONTEXT=stagger_ballhit_reaction_y07_2_0_090 kick_mid_3_3_adjust_y0_000 tacklefoot_far_3_0_000_legscissors_down sliding_2_0_090_parallel_R autoMove_41_parallel_to_back_3m_3_act064 autoMove_41_parallel_to_run_3_3m_far_act095 passGetMove_03_parallel_turn_3m_3m_090_act095 dm_oop_gk_cheer_riseup_facedown_lookaround_0_1_090 dm_oop_gk_sad_riseup_sideways_regret_0_0_f045 js_idle_0_0_135_guard_side_set013_of_act064 head_y06_sidle_chest_3_2_f090 head_y07_sidle_2_1_f090 head_y08_sidle_chest_3_0_f180_shed gkunderthrow_0_0_fast js_traprun_3_2_000_y0_out_guard_side_act064 gkprejump_2_3_y05_rotateStep_000_Otherside dm_

OFFSET=0xb06da6 TERM=turn
CONTEXT=t064 head_y06_sidle_chest_3_2_f090 head_y07_sidle_2_1_f090 head_y08_sidle_chest_3_0_f180_shed gkunderthrow_0_0_fast js_traprun_3_2_000_y0_out_guard_side_act064 gkprejump_2_3_y05_rotateStep_000_Otherside dm_oop_gk_lie_0_1_walkguts dm_oop_gk_turn_135_0_1_walkAngry js_slant_3_3_loop_guard_back_sub autoMove_03_crank90_loop_2_2_mid autoMove_05_zigzag135_front_loop_3_3_mid autoMove_07_ragged45_front_loop_1_1_STEP_mid autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_v2_mid coach_0_0_000_hands_waist_position_up dm_oop_calmdown_f090_idle dm_oop_linekeep_both_mid_delay_v2 autoMove_40_circle_short_run_tur

OFFSET=0xb06e7a TERM=turn
CONTEXT=_lie_0_1_walkguts dm_oop_gk_turn_135_0_1_walkAngry js_slant_3_3_loop_guard_back_sub autoMove_03_crank90_loop_2_2_mid autoMove_05_zigzag135_front_loop_3_3_mid autoMove_07_ragged45_front_loop_1_1_STEP_mid autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_v2_mid coach_0_0_000_hands_waist_position_up dm_oop_calmdown_f090_idle dm_oop_linekeep_both_mid_delay_v2 autoMove_40_circle_short_run_turn_3_3_short autoMove_06_zigzag135_side_loop_2_2_STEP_near autoMove_11_bodyangle_rolling_fast_1_1_mid_michael gkdeflectscoop_f01_3_0_y00 autoMove_07_ragged45_front_loop_3_3_STEP_near_gabriel autoMove_08_ragged45_s

OFFSET=0xb06f0f TERM=turn
CONTEXT=_3_3_mid autoMove_07_ragged45_front_loop_1_1_STEP_mid autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_v2_mid coach_0_0_000_hands_waist_position_up dm_oop_calmdown_f090_idle dm_oop_linekeep_both_mid_delay_v2 autoMove_40_circle_short_run_turn_3_3_short autoMove_06_zigzag135_side_loop_2_2_STEP_near autoMove_11_bodyangle_rolling_fast_1_1_mid_michael gkdeflectscoop_f01_3_0_y00 autoMove_07_ragged45_front_loop_3_3_STEP_near_gabriel autoMove_08_ragged45_slant_loop_1_1_STEP_near_gabriel autoMove_08_ragged45_slant_loop_3_3_STEP_near_gabriel autoMove_00_dribble_bodyangle_00_135_00_1_1_STEP_near_gabriel a

OFFSET=0xb07219 TERM=turn
CONTEXT=_gabriel ballTouch_05_5_dribble_touch_far_1_1_000_y0_gabriel nearDefense_04_BODYTURN_Slant_2_2_rightfront_STEP_near_gabriel autoMove_02_dribble_reverse_stop_rightfront_leftback_1_1_STEP_near_gabriel gkmovehigh_idle_0_0_135_ball feint_springturn_0_3_f067_y0_in_out_act097 dml_goal_celebrate_0279 js_run_dodge_045_set01_3_3_135_df_act064 js_run_interrupt_000_set01_3_3_000_of_act097 dm_oop_ballcome_handup_double_f090_walk_1_1_side_000 gknearmovestep_run_step_0_3_3 StabilizerCam_idle_0_1_walkside_L dm_oop_pointing_045_mid_delayside_1_1 F_ActualBattle_191007_F011_t03_Takayama_Fcut002 F_ActualBattle_20012

OFFSET=0xb07855 TERM=turn
CONTEXT=01_Gabriel_03 enum_dummy142 enum_dummy161 LongVersion_200127_F003_t01_Takayama enum_dummy195 enum_dummy215 enum_dummy246 gkgoalkick_inside_mid_0_0_090 enum_dummy273 enum_dummy276 autoMove_06_zigzag160_side_loop_1_2_3_warning_act080 dash_04_turn_4_4_180_act079 dash_04_turn_4_4_parallel_165_act079 dash_06_backslant_2_4_parallel_f045_act071 dash_06_slant_2_4_parallel_f135_act068 dm_oop_appeal_1_3_180_at135_act071 dm_oop_praise_1_3_090_at000_act064 dm_oop_praise_1_3_180_at090_act064_02 StabilizerCam_run_2_2 enum_dummy303 enum_dummy307 enum_dummy311 enum_dummy316 enum_dummy327 enum_dummy328 LongVersion

OFFSET=0xb07871 TERM=turn
CONTEXT=enum_dummy161 LongVersion_200127_F003_t01_Takayama enum_dummy195 enum_dummy215 enum_dummy246 gkgoalkick_inside_mid_0_0_090 enum_dummy273 enum_dummy276 autoMove_06_zigzag160_side_loop_1_2_3_warning_act080 dash_04_turn_4_4_180_act079 dash_04_turn_4_4_parallel_165_act079 dash_06_backslant_2_4_parallel_f045_act071 dash_06_slant_2_4_parallel_f135_act068 dm_oop_appeal_1_3_180_at135_act071 dm_oop_praise_1_3_090_at000_act064 dm_oop_praise_1_3_180_at090_act064_02 StabilizerCam_run_2_2 enum_dummy303 enum_dummy307 enum_dummy311 enum_dummy316 enum_dummy327 enum_dummy328 LongVersion_201123_F014_t01_act071_01 L

OFFSET=0xb07acb TERM=turn
CONTEXT= LongVersion_201123_F017_t01_act071_02 LongVersion_201123_F018_t01_act068_01 LongVersion_201123_F024_t01_act071_02 LongVersion_201123_F029_t01_act068_01 LongVersion_201124_F032_t01_act071_02 enum_dummy459 autoMove_33_01_gkmovenear_idle_idleturn_0_0 NEARKEEPER_04_03_gkmovemid_2_2_BODYTURN_SLANT NEARKEEPER_04_04_gkmovemid_3_3_BODYTURN_SLANT autoMove_11_bodyangle_rolling_slow_3_3_Back_to_Front_mid_michael enum_dummy482 enum_dummy522 enum_dummy538 enum_dummy569 enum_dummy573 ShortVersion_201123_F004_t01_act068_01 enum_dummy603 ShortVersion_201123_F016_t01_act071_01 enum_dummy652 defenseMove_01_paralle

OFFSET=0xb08a66 TERM=turn
CONTEXT=ndBack_3_1_0 demo_miss_hip_3_1 demo_miss_head_0_1 dm_oop_waitpose_045_walkback_1_2_run puntkick_highpunt_0_0 blockside_2_0_y00_sliding fall_lowbody_3_0_v3_l stagger_lowbody_0_0_l stagger_lowbody_4_4_tackle_v2_l stagger_ballhit_head_3_3 goalturn_guts_high2 demo_move_4_1_lineout_090 demo_gk_glad_18 demo_gk_glad_lie_8 demo_gk_glad_lie_10 demo_angry_hurry_1 demo_angry_hurry_18 demo_miss_0_1_bendback_090_1 demo_miss_3_1_hip_135 demo_miss_faceup_2 demo_appeal_hurry_3 demo_appeal_hurry_15 demo_contact_pain_045_2 demo_sorry_4_1_lineout_090 demo_praise_hurry_9 TimeUp_1_0_Droop_1_0 dodge_human_jump_3_v3 ela

OFFSET=0xb0bb83 TERM=turn
CONTEXT=LTS: Platforms other than Linux and Windows are not supported Server is done. "xds_server" field not present duplicate "channel_creds" field [%s %p] subchannel list %p index %lu: Created subchannel %p for address uri %s [RR %p picker %p] returning index %lu, subchannel=%p GRPC_ARG_DEFAULT_AUTHORITY channel arg. not found. Note that direct channels must explicitly specify a value for this argument. Cannot allocate buffer larger than kint32max for can't reach here. command_service.CommandRequest.id SetInt32 GetRepeatedUInt64 SetRepeatedFloat Protocol Buffer reflection usage error: Method : g

OFFSET=0xb0f585 TERM=turn
CONTEXT=`consumeFrame()` [CriVodStm] Failed to get current media segment info at onEndReadingHlsMediaSegment. Stream: %d, Segment: %d E2018122601:CriAesDecryptorAndroid failed to create JVM local frame. [CriAesSegmentsDecryptor] The get_url api returns invalid status(%d). Deal as DO_DEFAULT. E2021041101:There is no `WEBVTT` (line:%d) AndroidThunkJava_IsAllowedRemoteNotifications com/epicgames/ue4/GameActivity$InputDeviceInfo AndroidThunkJava_GetNativeDisplayRefreshRate android_main FTaskGraphInterface::Startup FShaderCodeLibrary::OpenLibrary PlayFirstPreLoadScreen etc LoadStartupModules ResolutionWidth 

OFFSET=0xb116d3 TERM=turn
CONTEXT=] Level = %d. Not Exec UE FADE IMPL : CheckFadingTimer: visibility:%d, fadeIn:%d(%f)(%f)(%d), fadeOut:%d(%f)(%f)(%d) RemoveCaptureForRender3D Online/Matching/Matching1vsAi Online/EvCompe/EventCompe/MenuEvCompeEventCompeGroupStageDrawCanReturn Online/EvCompe/GroupLeague/MenuEvCompeCpuLevelSelect Online/Lobby/StrikeArena/MenuStrikeArenaReward Online/Match/MatchOpponentInfo Match/Sugoroku/SugorokuInfoPlayerDetail Online/UserCompe/CompeInfo/MenuUserCompeGroupStageRecord Common/ContentList/MenuContentListAssetPreview Shop/Coin/MenuShopCoinPlayerDetail Online/Season/MenuSeasonRecordList Online/Season/

OFFSET=0xb12852 TERM=turn
CONTEXT=JumpBtnAlert CallbackEventEndAlert PresentRecvType::BingoMasu CallbackOverwrite ACTIONVIEW_ITEM_TYPE::ACTIONVIEW_ITEM_LINK PARENT_TYPE::RENTAL SetSide CallEventOnClose RotateDemoPlayerFinishCallback ESkillTrainingSegmentType::SEGMENT_MAX ReturnToAcquireableBigoList UpdateViewOnOverwrite MyClubPackAnnounceViewProceedUniformPreview__DelegateSignature TouchDisclaimerButton ESTANDARDPLAYERTICKET_ICON_TYPE::ESTANDARDPLAYERTICKET_ICON_TYPE_NATION ESTANDARDPLAYERTICKET_ICON_TYPE::ESTANDARDPLAYERTICKET_ICON_TYPE_LEAGUE CallbackDeleted OnStartFadeOut ItemIndex m_pActionView detailViewBtnStr OnAnnounceViewP

OFFSET=0xb1747f TERM=turn
CONTEXT=tanceBoundsList ShowDebugToggleSubCategory TextureUWidth TextureVHeight EImportanceWeight::Red BreakImportanceTexture SampleSize InputActionHandlerDynamicSignature__DelegateSignature EControllerAnalogStick bEnableGestureRecognizer bShouldReturnIndices EdSectionStart EdSectionEnd CameraAnimInst bUseCustomEventName LastUpdatePosition InstancedTrack UnsignedInt32Variable SignedInt32Variable Array_Append SetArrayPropertyByName FilteredArray Conv_GuidToString Parse_StringToGuid PointerEvent_GetWheelDelta TextCategory Abs_Int64 BMax EqualEqual_ObjectObject FromDays GetMinutes GetPointDistanceToLine GetT

OFFSET=0xb198fc TERM=turn
CONTEXT=0_f090 feint_outin_0_3_045_y0_act064 gkmovenear_sidestagger_3_3 gkprejump_3_0_rotateStep_045 gkpunch_f00_0_0_y10_palm gkpuntkick_front_nearline_0_0_cancel gkrise_faceup_0_0_000 gkrise_sideways_l_0_3_000 gkstagger_catch_0_0_y10_f090 goalnet_turn_160_rapid head_y06_3_0_090_far_dive head_y07_0_0_f090_side head_y09_3_0_000 head_y09_sidle_3_0_000 idle_0_3_run_000 kick_long_0_0_instep_y2_f045 kick_mid_0_0_inside_y0_045_punch kick_mid_0_0_inside_y0_f045_side kick_mid_0_0_instep_y2_045_side kick_mid_3_0_inside_y0_045_far kick_mid_3_0_outside_y0_000_far kick_mid_3_0_outside_y0_f090_far_down kick_short_0_0_

OFFSET=0xb1a14b TERM=turn
CONTEXT=097 feint_trap_0_3_f315_y5_back_ver12 trap_0_0_000_y0_lobball_sole_ver23 stagger_ballhit_reaction_y03_0_0_000_v2 autoMove_32_go_to_0_2_parallel_180_act064 blockhead_0_0_y09_f090_side blockhead_side_2_0_y05_f180_down passGetMove_03_parallel_turn_3m_3m_045_act095 dm_goal_jog_2_4_dashGutsR_090 dm_oop_gk_cheer_idle_handsup_side_0_0_090 dm_oop_gk_riseup_0_1_sideways_attention_000 dm_oop_gk_sad_riseup_sideways_regret_0_0_000 block_0_0_y00_f090_far_down_onehand_quick block_0_0_y00_f090_near_rear head_y09_sidle_3_0_f090_clear_down head_y09_sidle_3_0_f180_clear_down_v2 gkdropball_3_0_fast js_run_4_4_000_gu

OFFSET=0xb1a3dc TERM=turn
CONTEXT=_01_reverse_loop_parallel_back_2_2_mid autoMove_04_crank45_loop_1_1_mid coach_0_0_000_normal_oop_protest_2 dm_oop_beckon_f180_side_3_3_000 ballboy_idle_loop autoMove_08_ragged45_slant_loop_2_2_STEP_near autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_STEP_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_v2_mid_michael autoMove_10_bodyangle_keep_circle_smallturn_front_1_1_STEP_mid_michael autoMove_11_bodyangle_rolling_fast_3_3_mid_michael head_y09_jostle_s_0_0_f090_act064 autoMove_06_dribble_zigzag135_side_loop_3_3_mid_gabriel avoidjumpsliding_3_4_022_act068_01 autoMove_01_revers

OFFSET=0xb1a421 TERM=turn
CONTEXT=id coach_0_0_000_normal_oop_protest_2 dm_oop_beckon_f180_side_3_3_000 ballboy_idle_loop autoMove_08_ragged45_slant_loop_2_2_STEP_near autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_STEP_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_v2_mid_michael autoMove_10_bodyangle_keep_circle_smallturn_front_1_1_STEP_mid_michael autoMove_11_bodyangle_rolling_fast_3_3_mid_michael head_y09_jostle_s_0_0_f090_act064 autoMove_06_dribble_zigzag135_side_loop_3_3_mid_gabriel avoidjumpsliding_3_4_022_act068_01 autoMove_01_reverse_loop_front_back_1_1_STEP_near_gabriel autoMove_02_reverse_stop_left

OFFSET=0xb1a466 TERM=turn
CONTEXT= ballboy_idle_loop autoMove_08_ragged45_slant_loop_2_2_STEP_near autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_STEP_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_v2_mid_michael autoMove_10_bodyangle_keep_circle_smallturn_front_1_1_STEP_mid_michael autoMove_11_bodyangle_rolling_fast_3_3_mid_michael head_y09_jostle_s_0_0_f090_act064 autoMove_06_dribble_zigzag135_side_loop_3_3_mid_gabriel avoidjumpsliding_3_4_022_act068_01 autoMove_01_reverse_loop_front_back_1_1_STEP_near_gabriel autoMove_02_reverse_stop_leftfront_rightback_2_2_STEP_near_gabriel autoMove_03_dribble_crank90_loo

OFFSET=0xb1b32f TERM=turn
CONTEXT=SOLVE *:%d using wildcard Unsupported HTTP/1 subversion in response cr-exp100 Done waiting for 100-continue chunk hex-length not valid: '%s' %x Sat Saturday %4ldG end of response with %ld bytes missing Could not seek stream seek callback returned error %d ioctl callback returned error %d cr-buf header cannot complete SOCKS4 connection to %d.%d.%d.%d:%d. (%d), request rejected or failed. FTP: unknown PASS reply Send failed since rewinding of the data stream failed .? HTTPS-proxy could not open PKCS12 file '%s' subjectAltName: host "%s" matched cert's "%s" SSL shutdown finished SSL_ERROR_NONE SSL c

OFFSET=0xb1b350 TERM=turn
CONTEXT=rted HTTP/1 subversion in response cr-exp100 Done waiting for 100-continue chunk hex-length not valid: '%s' %x Sat Saturday %4ldG end of response with %ld bytes missing Could not seek stream seek callback returned error %d ioctl callback returned error %d cr-buf header cannot complete SOCKS4 connection to %d.%d.%d.%d:%d. (%d), request rejected or failed. FTP: unknown PASS reply Send failed since rewinding of the data stream failed .? HTTPS-proxy could not open PKCS12 file '%s' subjectAltName: host "%s" matched cert's "%s" SSL shutdown finished SSL_ERROR_NONE SSL certificate problem: %s Could not 

OFFSET=0xb1bc52 TERM=turn
CONTEXT=_fk_indirect_loop linesman_goalkick linesman_2_2_side seamless_ck_ball_set_2_0_l blockfront_0_0_y00_shoot_reaction blockfront_0_0_y04_shoot_reaction_v2 fall_lowbody_0_0_r fall_lowbody_4_0_v6_r stagger_upbody_0_0 stagger_upbody_2_2_hard goalturn_guts3 demo_gk_glad_17 demo_angry_3_1_045 demo_gk_angry_lie_4 demo_angry_hurry_7 demo_miss_0_0_faceup demo_droop_hurry_2 demo_appeal_3_0_at135_3_pat_2 demo_cheer_instruct_at045_1 demo_praise_hurry_21 TimeUp_3_0_Droop_1_0 HalfEnd_1_1_Normal HalfEnd_0_1_Droop_0_0 dodge_human_slide_3_3 dodge_human_stop_2 dodge_net_0_3_slow dodge_post_3_0 doubletouch_0_3_l doubl

OFFSET=0xb1f852 TERM=turn
CONTEXT=ayStart Online/Quick/QuickProcessEnd Online/Lobby/ProcLobbyRoomSetParameterMatch Online/EvCompe/MlEvent/ProcEvCompeEventInit Online/EvCompe/MlEvent/ProcMlEventPreGamePlan Online/UserCompe/ProcUserCompeRootInit match_end introduction_demo return_ranking return_user_compe_lobby cpk_snd/common/sound/config/Chant/ BGM0_ORG_FASTEST_GOAL_COLLABO_02 cpk_snd/%s/sound/config/Control/tree_control.xml SA_C_NMB_E12 SA_C_NMB_E53 SA_C_NMB_E57 SA_C_NMB04 SA_C_NMB08 SA_C_NMB13 SA_C_NMB43 SA_C_NMB72 SA_C_NMB78 DevelopData/soundScript/develop/Script/Xml_Mobile/Common/PitchSound/Tree/ =' &apos; %s_%s_%s%04d %s_%s_%s

OFFSET=0xb1f861 TERM=turn
CONTEXT=Quick/QuickProcessEnd Online/Lobby/ProcLobbyRoomSetParameterMatch Online/EvCompe/MlEvent/ProcEvCompeEventInit Online/EvCompe/MlEvent/ProcMlEventPreGamePlan Online/UserCompe/ProcUserCompeRootInit match_end introduction_demo return_ranking return_user_compe_lobby cpk_snd/common/sound/config/Chant/ BGM0_ORG_FASTEST_GOAL_COLLABO_02 cpk_snd/%s/sound/config/Control/tree_control.xml SA_C_NMB_E12 SA_C_NMB_E53 SA_C_NMB_E57 SA_C_NMB04 SA_C_NMB08 SA_C_NMB13 SA_C_NMB43 SA_C_NMB72 SA_C_NMB78 DevelopData/soundScript/develop/Script/Xml_Mobile/Common/PitchSound/Tree/ =' &apos; %s_%s_%s%04d %s_%s_%s%06d TaPortKank

OFFSET=0xb1ffe0 TERM=turn
CONTEXT=ly threw an exception bad_array_new_length (anonymous namespace) operator&= operator>>= operator% >> SV.startsWith("basic_") restrict char32_t future unspecified iostream_category error ampersand Articulation link initialization failed: returned NULL. RigidBody::setRigidBodyFlag: kinematic bodies with CCD enabled are not supported! CCD will be ignored. PxRigidStatic::setGlobalPose: Actor is part of a pruning structure, pruning structure is now invalid! static const char *physx::shdfnd::ReflectionAllocator<physx::PxBaseTask *>::getName() [T = physx::PxBaseTask *] static const char *physx::shdfnd::

OFFSET=0xb21927 TERM=turn
CONTEXT= frame buffer to user's buffer. E2004090214 ()Landroid/media/MediaCodecInfo$VideoCapabilities; E2020082731:Failed to create decoder. E2017062790:Ambisonics audio playback is not supported. CriManaSoundEx W2019052099:pthread_getschedparam returned an unusual value. Force the normal value to be set. E2011011801:setpriority() is failed. CriUsfDmxOut E2017122213:ACF file is not registered. E2017122216:ACF file is not registered. W2013080813:Specified aisac control '%s' is not found. E2017122242:ACF file is not registered. E2017122248:ACF file is not registered. CRIWARE/Delay CRIWARE/Chorus CRIWARE/Bus

OFFSET=0xb26ac3 TERM=turn
CONTEXT=gedAcceptOpenSideLeaderSetting ELobbyRoomReqest::OnChangedAcceptSwitchInformation ELobbyRoomReqest::FadeAchievementTaskList ELobbyRoomReqest::FadeMatchHistory ELobbyRoomAlertKind::OpponentWaitSingle ELobbyRoomActionKind::Reward ResetAgingReturn actionKind CS_FriendDataPtr IconPtr ELayoutMatchMainMenuEventCoopLobbyChoiceIcon Btn4Ptr MessageStr BonusHeadlineStr roomInfoList errorKind StartSwitchMatchReady ELobbyRoomMatchSettingsItem::SIDE ELobbyRoomMatchSettingsItem::NUM LobbyMatchTimeInfo matchEnv ELoginBonusPresentType::PRESENT_TYPE_ITEM EMenuMailboxReceiveAlertType::RECEIVE_ALERT_ALL_PART EMenuMa

OFFSET=0xb29997 TERM=turn
CONTEXT= GetAllAssets SessionId EGameplayTagQueryExprType::Undefined EComputeNTBsOptions::Normals IsEdgeInternalToPolygon ReserveNewVertices SetPolygonVertexInstance OrphanedPolygonGroupsPtr VertexNumber PerFrameKB PakFile_SerializePathHashIndex ReturnBufferAlignment NumInfluences FixationPoint EMediaAudioCaptureDeviceFilter::Software GetVideoTrackAspectRatio Vertical CurrentAspectRatio CopyMetaData SetBinding CreateLevelSequencePlayer G:/UE4.26_eFB/Base/Engine/Source/Runtime/Engine/Classes/AI/Navigation/NavCollisionBase.h OnInputTouchLeave TileCount ViewportMisc UpY Advertising G:/UE4.26_eFB/Base/Engine/

OFFSET=0xb2d824 TERM=turn
CONTEXT=_0_y04 new_dribble_0_3_f135_y0_sole_act064 dm_oop_pointing_f090_side_1_0_idle_000 dm_oop_waitpose_f045_idle_0_1_sidestop_045 dm_oop_ballcome_f090_parallel_2_2_parallel_000 gksavingCancel_beforeblock_f03 js_back_1_1_loop_guard_back_main_halfturn_v2 loop_3_3_045_run_near_act064 kick_long_0_0_instep_y2_000_compact D_PES_20251203_K06_001_kubo_03_Fcut001 dml_goal_celebrate_0142 dm_oop_pointing_f135_mid_delayside_1_1 dm_oop_waitpose_000_walkback_1_1 dm_oop_waitpose_f090_run_2_3_000 ActualBattle_181002_F100_t03_Gabriel ActualBattle_200127_F025_t02_Oriul new_dribblerun_3_2_090_sidenearRev_y0_near_in_ver12

OFFSET=0xb2dd8d TERM=turn
CONTEXT=rsion_171104_F111_t01_Gabriel_02 new_dribble_0_3_180_axisback_sole enum_dummy150 enum_dummy151 LongVersion_200127_F004_t01_Gabriel enum_dummy223 enum_dummy231 enum_dummy242 dml_goal_celebrate_0210 enum_dummy280 autoMove_40_circle_short_run_turn_3_3_bodyangle_keep_act079 dash_06_back_2_4_parallel_090_act079 dash_07_dash_4_1_walk_ball_follow_act071 pull_ball_foot_2_0_180 dm_oop_gk_riseup_0_0_sideways_walkGuts_000 dm_oop_gk_sidestep_2_0_mortifying_000 enum_dummy299 dm_oop_angry_1_3_180_act071_01 dm_oop_angry_3_3_180_act071_02 dm_oop_praise_1_3_000_at090_act071_02 dm_oop_praise_1_3_090_atf090_act071_0

OFFSET=0xb2ec85 TERM=turn
CONTEXT=a_person_move_back_2_0 demo_miss_face_0_2 demo_miss_HandOnKnee_0_0 dm_oop_pointing_000_walk_1_1_walkback dm_miss_sidestep_1_2_jog_angry_high demo_coop_talk_1 goalkick_inside_r kickoff_loop_cheer linesman_1_1_side linesman_3_3_side linesman_turn_1_1_walk seamless_ck_ball_set_3_0_r seamless_stepback blockfront_0_0_y02 blockfront_0_0_y07_shoot_reaction fall_lowbody_3_0_v4_r fall_lowbody_4_0_v3_r fall_lowbody_3_0_sliding_high_r stagger_upbody_0_0_guard goalturn_guts_2_4 goalturn_pointing_comeon_2_4 demo_move_tired_sweat demo_glad_0_1_135 demo_gk_glad_lie_6 demo_angry_0_1_045_3 demo_angry_hurry_20 demo

OFFSET=0xb2ed5e TERM=turn
CONTEXT=sman_3_3_side linesman_turn_1_1_walk seamless_ck_ball_set_3_0_r seamless_stepback blockfront_0_0_y02 blockfront_0_0_y07_shoot_reaction fall_lowbody_3_0_v4_r fall_lowbody_4_0_v3_r fall_lowbody_3_0_sliding_high_r stagger_upbody_0_0_guard goalturn_guts_2_4 goalturn_pointing_comeon_2_4 demo_move_tired_sweat demo_glad_0_1_135 demo_gk_glad_lie_6 demo_angry_0_1_045_3 demo_angry_hurry_20 demo_miss_0_1_bendback_045_1 demo_miss_0_1_bendback_135_2 demo_miss_1_1_back demo_gk_miss_1 demo_cheer_at135 demo_praise_hurry_22 demo_goal_extra_loop_0002 TimeUp_0_0_Grad_2_0 TimeUp_0_1_Grad_0_0 doubletouch_quick_0_3_l d

OFFSET=0xb2ed70 TERM=turn
CONTEXT=sman_turn_1_1_walk seamless_ck_ball_set_3_0_r seamless_stepback blockfront_0_0_y02 blockfront_0_0_y07_shoot_reaction fall_lowbody_3_0_v4_r fall_lowbody_4_0_v3_r fall_lowbody_3_0_sliding_high_r stagger_upbody_0_0_guard goalturn_guts_2_4 goalturn_pointing_comeon_2_4 demo_move_tired_sweat demo_glad_0_1_135 demo_gk_glad_lie_6 demo_angry_0_1_045_3 demo_angry_hurry_20 demo_miss_0_1_bendback_045_1 demo_miss_0_1_bendback_135_2 demo_miss_1_1_back demo_gk_miss_1 demo_cheer_at135 demo_praise_hurry_22 demo_goal_extra_loop_0002 TimeUp_0_0_Grad_2_0 TimeUp_0_1_Grad_0_0 doubletouch_quick_0_3_l doubletouch_quick_0

OFFSET=0xb311cc TERM=turn
CONTEXT=g_state != nullptr INVALID_ARGUMENT PERMISSION_DENIED userinfo found in proxy URI starting health watch chand=%p calld=%p: disabling retries before first attempt PendingBatchesResume chand=%p: disconnect_with_error: %s chand=%p: resolver returned no service config. Using default service config provided by client API. resolver requested LB policy %s but provided at least one balancer address -- forcing use of grpclb LB policy grpc.client_channel_factory Handshake timed out Failed HTTP requests to all targets [cdslb %p] Using xds client %p from channel call_ != nullptr [xds_client %p] ADS call statu

OFFSET=0xb38ed7 TERM=turn
CONTEXT=wEnd__DelegateSignature ExtraInfoAnimatedWidgetPtr EMenuTopMatchInitStep::CheckInvitationFlow m_pResult EMenuAchievementReceiveResult::RECEIVE_RESULT_FAIL_UNIQUE CreateDetailViewWeb ShowAlertForceCancelAgreement ParentWindow PopupAlertForReturnCoinIfNeeded EAgentRarityType::AGENT_RARITY_RARE ECmnIconRewardType::TYPE_UNIFORM EPresentReason::PRESENT_REASON_CUSTOM_LEAGUE_COM_RANKING EItemType::ITEM_TYPELEVEL_TRAINING StandardIconType ECmnPlayerDetailHeaderType::PLAYER_DETAIL_HEADER_TALENT_POINT EMenuPlayerDetailBoosterEffectingType rotationStrId m_boosterTypeStr m_targetCategoryStr2 SetBoosterWidget 

OFFSET=0xb3b137 TERM=turn
CONTEXT=nknown percent [%lc%lc%lc] in FGenericWidePlatformString::GetVarArgs() [%s] . Unknown percent [%%%c] in FGenericWidePlatformString::GetVarArgs(). other UInt32Property VoiceChat UClassRegisterAllCompiledInClasses EAutomationEventType EAppReturnType::Continue EUnit::Meters EUnit::Inches EUnit::Kelvin EUnit PF_DXT1 PF_FloatRGB ESearchDir::FromStart ESearchDir::FromEnd PolyglotTextData Enter Decimal F3 Global_Menu ValveIndex_Left_Trigger_Click ValveIndex_Right_Trigger_Touch ValveIndex_Right_Trackpad_Down 7 ` ETouchIndex::Type EControllerHand::Special_1 setLooping RegionChanged com/epicgames/ue4/Media

OFFSET=0xb402e6 TERM=turn
CONTEXT=k_handclap_low gkcollapsingnear_s01_0_0_y06 block_0_0_y03_f090_near_thigh passGetMove_03_parallel_run_3m_3m_act096 dm_oop_gk_glad_idel_guts_under_0_1_090 dm_oop_gk_glad_riseup_facedown_dubbleguts_0_1_090 dm_oop_gk_glad_riseup_sideways_guts_turn_0_1_135 BallBoy_Downthrow sliding_side_2_0_f180 head_y06_sidle_2_1_f090_shed js_run_3_3_000_guard_side_set004_df_win_act064 js_run_4_4_000_guard_side_set015_pulled_df_act064 trap_boundball_0_3_000_y4_breast_ver23 gkoverthrow_0_0_hard_cancel dm_oop_gk_side_3_0_upside_seeOff dm_oop_gk_idle_0_0_idle_mortfying_04 autoMove_01_reverse_loop_front_back_3_3_STEP_mid

OFFSET=0xb404db TERM=turn
CONTEXT=3_0_upside_seeOff dm_oop_gk_idle_0_0_idle_mortfying_04 autoMove_01_reverse_loop_front_back_3_3_STEP_mid autoMove_01_reverse_loop_slant_backslant_1_1_mid autoMove_01_reverse_loop_slant_backslant_2_2_mid coach_0_0_000_hands_waist autoMove_30_turn_move_3_3_CRANK_mid dm_oop_ballcome_000_side_2_2_run_000 autoMove_05_zigzag135_front_loop_3_3_STEP_mid_michael autoMove_07_dribble_ragged45_front_loop_2_2_mid_gabriel coach_0_1_f090_cross_arms_oop_disappointing autoMove_04_dribble_crank45_loop_2_2_mid_gabriel gkgoalkick_Quick_long_0_0_000_front new_dribble_0_4_090_in_ver1 autoMove_00_bodyangle_00_180_00_1_1_

OFFSET=0xb4066d TERM=turn
CONTEXT=_gabriel coach_0_1_f090_cross_arms_oop_disappointing autoMove_04_dribble_crank45_loop_2_2_mid_gabriel gkgoalkick_Quick_long_0_0_000_front new_dribble_0_4_090_in_ver1 autoMove_00_bodyangle_00_180_00_1_1_STEP_near_gabriel autoMove_30_dribble_turn_move_2_2_CRANK_near_gabriel ballTouch_04_4_dribble_player_move_0_3_f135_y0_gabriel autoMove_02_dribble_reverse_stop_front_back_1_1_STEP_near_gabriel autoMove_02_dribble_reverse_stop_rightfront_leftback_2_2_STEP_near_gabriel nearDribble_04_1_dribble_burst_0_4_135_y0_oriul nearDribble_04_1_dribble_burst_1_4_180_y0_oriul dm_oop_lineup_090_walkback_1_1_walk_090

OFFSET=0xb41ffd TERM=turn
CONTEXT=mo_goal_head_sliding demo_pfm_provocation_3_3_r goalkick_instruction_0_r goalkick_instruction_1_l goalkick_idle_l throw_under_0_0_cancel judge_point_to_1 linesman_corner_fromflagup seamless_catch_3_3_y5 seamless_catch_3_3_y0 seamless_catch_turn_0_0_y6 seamless_pull_ball_foot_2_0 seamless_stepback_cancel blockfront_4_0_y00 blockside_3_0_y02_sliding stagger_lowbody_4_4_tackle_r goalturn_dash_0_4 demo_glad_1_0_000 demo_gk_glad_10 demo_gk_glad_lie_9 demo_angry_0_1_135_4 demo_gk_angry_8 demo_angry_hurry_3 demo_miss_0_1_droop_135_3 demo_praise_hurry_3 HalfEnd_3_1_Normal_2 HalfEnd_1_1_Normal_3 kickfeint_

OFFSET=0xb4208c TERM=turn
CONTEXT=point_to_1 linesman_corner_fromflagup seamless_catch_3_3_y5 seamless_catch_3_3_y0 seamless_catch_turn_0_0_y6 seamless_pull_ball_foot_2_0 seamless_stepback_cancel blockfront_4_0_y00 blockside_3_0_y02_sliding stagger_lowbody_4_4_tackle_r goalturn_dash_0_4 demo_glad_1_0_000 demo_gk_glad_10 demo_gk_glad_lie_9 demo_angry_0_1_135_4 demo_gk_angry_8 demo_angry_hurry_3 demo_miss_0_1_droop_135_3 demo_praise_hurry_3 HalfEnd_3_1_Normal_2 HalfEnd_1_1_Normal_3 kickfeint_0_0_y0_notouch_samba_l kickfeint_valdivia_3_3_l lfeint_3_3_l roulettesingle_3_3_r shakefootkicktheground_0_0_r shakefootonce_0_0_r head_3_0_y6_

OFFSET=0xb43aa0 TERM=turn
CONTEXT=rnNetworkIoTcpConnectionTimeoutMs TurnNetworkIoDegradedLatencyRatio DcTestNumWorker NetworkTesterPingTimeoutMs PingRequestTimeoutUs LinkUpMode KeyExcahngeRetransmissionTimeoutUs P2P_ADHOC_WIFIDIRECTLAN_LOW_LEVEL P2P_ADHOC_LAN direct_online_turn_mode NetworkQualityIndicator ps f2p RESPONSE_ADDRESS RP_SYNC_POINT |->> [ %s ][ %d ] URLBase TurnInitializedNatType RevokeConnectivity uds E_NOMEM E_NOTFOUND E_UPNP_DEVICE_NOT_FOUND E_TURN_NOT_AVAILABLE UPNP_DISCOVERY_FULL_COMPLETE START_UDP_HOLE_PUNCHING_ADVICE_CANCEL_HAIRPIN jnihelper ] is already registered! ANDROID Windows nsw NATTYPEV6 SEND_COMMAND_D

OFFSET=0xb43d7f TERM=turn
CONTEXT=RECEIVED_COMMAND_COUNT RECEIVED_VALID_COUNT SENT_VOICE_DATA_COUNT_INMATCH AWAY_TEAM_ID_NO TURN_SESSION_RTT_EWMA P2PTURNIO_P2P_RTT_Mean TURN_TCP MAIN_THREAD_ELAPSED_SINCE_LAST_UPDATED VALUE need_root_box_warn_due_to_age CmdSendNotice ticket turn_server_list SendAdjustParamTask 10BASE_HALF WIMAX DisableBroadcasting grpc.http2.write_buffer_size grpc.keepalive_permit_without_calls grpc.xds_locality_retention_interval_ms plugin_credentials grpc_channel_arguments G:/PES22HC/Dev-600Series/Source/Shared/basic/ext/grpc/grpc/include/grpcpp/impl/codegen/proto_buffer_writer.h G:\PES22HC\Dev-600Series\Source\S

OFFSET=0xb4e7f8 TERM=turn
CONTEXT=e/Components/HorizontalBox.cpp SRichTextBlock OnMouseButtonDownEvent OnCheckStateChanged SetRadius PieceImage FindOptionIndex EDynamicBoxType HintText KeyboardType SetLayer SelectedKey NoKeySpecifiedText NavigateToIndex SetSelectionMode bReturnFocusToSelection BP_OnItemDoubleClicked TopCurve bIsReadOnly AngleBetweenItems SetDefaultTextStyle DecoratorClasses InUserSpecifiedScale InMaxAspectRatio AbsoluteScalar ESlateSizeRule::Type AccessibleText OnFloatValueChangedEvent__DelegateSignature bAnimateHorizontally SlotPadding MinDesiredSlotWidth CancelLatentActions GetOwningPlayerCameraManager SetDesire

OFFSET=0xb4ec7b TERM=turn
CONTEXT=E4.26_eFB/Base/Engine/Source/Runtime/PacketHandlers/PacketHandler/Classes/HandlerComponentFactory.h CreatePolygon GetPolygonVertices GetVertexConnectedTriangles SetVertexInstanceUV EPropertyAccessObjectType::WeakObject PropertyAccessPath ReturnBufferSize GetNumSubsteps OnMediaPlayerMediaOpenFailed__DelegateSignature GetTrackDisplayName SetMediaPlayer InFrequenciesToAnalyze GetAspectRatio RemoveBindingByTag ResetBinding LevelSequenceBindingReference FileName AudioCaptureProtocolType AdditionalCommandLineArguments GetCaptureFrameNumber EMovieSceneCaptureProtocolState::Initialized InFrameMetrics Char

OFFSET=0xb52893 TERM=turn
CONTEXT=op_2_2_STEP_mid coach_0_0_000_normal dm_oop_ballcome_handup_one_far_f045_idle_0_1_backslant dm_oop_linekeep_both_mid_delay autoMove_07_ragged45_front_loop_3_3_mid_michael dml_goal_celebrate_0336 head_y09_jostle_f_0_0_090_act097 autoMove_30_turn_move_2_2_CRANK_mid_michael avoidjumpsliding_3_4_045_act068_01 autoMove_04_crank45_loop_1_1_STEP_near_gabriel autoMove_00_dribble_bodyangle_00_135_00_3_3_STEP_near_gabriel autoMove_07_dribble_ragged45_front_loop_2_2_STEP_near_gabriel dash_04_turn_4_4_090_CIRCLE_Oriul dash_06_side_1_4_run_Oriul dash_06_walk_1_4_run_Oriul dash_10_walk_1_4_135_dash_Oriul reacti

OFFSET=0xb52989 TERM=turn
CONTEXT=ove_2_2_CRANK_mid_michael avoidjumpsliding_3_4_045_act068_01 autoMove_04_crank45_loop_1_1_STEP_near_gabriel autoMove_00_dribble_bodyangle_00_135_00_3_3_STEP_near_gabriel autoMove_07_dribble_ragged45_front_loop_2_2_STEP_near_gabriel dash_04_turn_4_4_090_CIRCLE_Oriul dash_06_side_1_4_run_Oriul dash_06_walk_1_4_run_Oriul dash_10_walk_1_4_135_dash_Oriul reaction_contact_0_2_135_act071_02 moveAdjust_05_Slant_FrontBack_3_3_gabriel nearDefense_04_BODYTURN_Slant_2_2_rightback_STEP_near_gabriel autoMove_02_dribble_reverse_stop_leftside_rightside_2_2_STEP_near_gabriel gkclear_f03s03_0_3_045 nearDribble_04_1

OFFSET=0xb53488 TERM=turn
CONTEXT=ARKEEPER_03_01_gkmovenear_0_1_0 enum_dummy466 enum_dummy480 enum_dummy507 enum_dummy517 enum_dummy529 enum_dummy548 enum_dummy576 enum_dummy599 enum_dummy602 enum_dummy616 defenseMove_01_neardelayback_3_3_parallel_045_act071 gkmovenear_stopturn_3_0 LongVersion_180929_F051_t03_Gabriel_02 face angr_brwup_talk_around_soft base_d_end_photo_call base_syucyu_me_ue dml_smil_soft ef23_pain_grit_loop ef23_protest_angry ef23_protest_shout ef23_smile_talk_laugh ef23_tackle_grimace_short loss_brwnit_grit_puff_blink_hard_slow loss_grit_eyhc_lith neut_breath_short_S_02 neut_mho_long pose_angry_S_06 pose_angry_t

OFFSET=0xb59b44 TERM=turn
CONTEXT=s an unpaired surrogate last regular permyriad UGW megabit kilometer dnam decimalFormat -Zero PIXEL_SIZE SIZE SUPERSCRIPT_SIZE WEIGHT_NAME CIDMapOffset SDBytes dup winfonts -polyton an- missing LZ dictionary unexpected zlib return invalid embedded Abstract ICC profile unexpected NamedColor ICC profile class sCAL height png_image_begin_read_from_memory: incorrect PNG_IMAGE_VERSION PNG unsigned integer out of range using zstream cHRM Blue X png_set_keep_unknown_chunks: invalid keep Compression buffer size cannot be changed because it is in use png_set_unknown_chunks now expects a vali

OFFSET=0xb5eb06 TERM=turn
CONTEXT=d IsSelectedEventTeamSelectOnlyOne SetDefaultGameMode SetSelectedEventId EMenuEvCompeMainMenuPresentStep::Trophy EMenuEvCompeMainMenuState::CheckPresentAlert EMenuEvCompeMainMenuState::RatingChangeAlertWait EMenuEvCompeMainMenuState::WaitReturnFade isEnableMatch IsNeedPopupRankingEventBeforeMatchView StartTaskSetCrossPlatformOption outRewardInfo EMenuEvCompeEventRankingStartCommandType::Next ageCategory GetCpuLevel pUserWidget unavailableInGameStr dispList ELinkAnimeLoop m_staminaRate m_initialCompetitionId ClosedToolTipMultiFormation GetLinkKind IsCoopBrowseOnly IsDispVoidPlayerAlertDialog IsNeed

OFFSET=0xb65717 TERM=turn
CONTEXT=igzag135_front_loop_3_3_STEP_mid coach_0_0_000_hands_waist_position_adjust_high dm_oop_lineup_f090_walk_1_2_run_000 dm_oop_pass_point_f045_run_2_2_f045 autoMove_00_bodyangle_00_90_f90_00_2_2_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_face_only_mid_michael autoMove_30_turn_move_2_2_CIRCLE_mid_michael quick_restart_step_stagger Slower_0_3_045 avoidjumpsliding_2_4_045_act068_01 autoMove_01_reverse_loop_front_back_3_3_STEP_near_gabriel autoMove_01_reverse_loop_side_3_3_STEP_near_gabriel autoMove_01_reverse_loop_slant_backslant_1_1_STEP_near_gabriel autoMove_02_reverse_stop_rightfr

OFFSET=0xb65748 TERM=turn
CONTEXT=nds_waist_position_adjust_high dm_oop_lineup_f090_walk_1_2_run_000 dm_oop_pass_point_f045_run_2_2_f045 autoMove_00_bodyangle_00_90_f90_00_2_2_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_face_only_mid_michael autoMove_30_turn_move_2_2_CIRCLE_mid_michael quick_restart_step_stagger Slower_0_3_045 avoidjumpsliding_2_4_045_act068_01 autoMove_01_reverse_loop_front_back_3_3_STEP_near_gabriel autoMove_01_reverse_loop_side_3_3_STEP_near_gabriel autoMove_01_reverse_loop_slant_backslant_1_1_STEP_near_gabriel autoMove_02_reverse_stop_rightfront_leftback_1_1_STEP_near_gabriel autoMove_02_re

OFFSET=0xb668b4 TERM=turn
CONTEXT=chunked transfer encoding on connection using HTTP version 2 or higher Illegal STS header skipped Proxy-authorization HTTP-PROXY Operation timed out after %ld milliseconds with %ld out of %ld bytes received Apr %4ldM cr_in_read, callback returned CURL_READFUNC_PAUSE Write callback asked for PAUSE when not supported cannot complete SOCKS4 connection to %d.%d.%d.%d:%d. (%d), request rejected because SOCKS server cannot connect to identd on the client. cannot complete SOCKS4 connection to %d.%d.%d.%d:%d. (%d), request rejected because the client program and identd report different user-ids. FTP: The 

OFFSET=0xb6715e TERM=turn
CONTEXT=mo_gutsR_0_0 goalkick_coaching_up_r puntkick_side_0_0_cancel seamless_carry_ball_back_2_2 blockfront_2_0_y01_shoot_reaction_v2 blockfront_2_0_y02_shoot_reaction_v3 blockside_2_0_y04 fall_lowbody_3_0_r fall_upbody_3_0 fall_upbody_4_0_v3 goalturn_low_hyper demo_gk_glad_8 demo_gk_glad_lie_3 demo_miss_3_1_bendback_135 demo_miss_3_1_droop_135 demo_miss_0_1_head_135_2 demo_miss_3_1_head_090 demo_miss_1_1_side_face demo_miss_facedown_135_1 trapstep_135_0_3_y0_sole demo_droop_hurry_3 demo_gk_appeal_lie_1 demo_gk_cheer_3 demo_contact_pain_135_2 demo_contact_pain_135_3 demo_praise_hurry_10 TimeUp_1_1_Grad_0

OFFSET=0xb69ca4 TERM=turn
CONTEXT=eld:maxAttempts error:should be of type number initialBackoff UNAUTHENTICATED chand=%p calld=%p: call failed but recv_trailing_metadata not started; starting it internally recv_trailing_metadata_ready for pending batch chand=%p: resolver returned updated service config: "%s" [grpclb %p] Re-resolution requested from %schild policy (%p). send_message_payload_ == nullptr ssl_creds != nullptr client_secret grpc_compute_engine_credentials_create(reserved=%p) pem_root_certs != nullptr fopen Verify peer callback returned a failure (%d) G:\PES22HC\Dev-600Series\Source\Shared\basic\ext\grpc\grpc\src\core\t

OFFSET=0xb69db5 TERM=turn
CONTEXT=s" [grpclb %p] Re-resolution requested from %schild policy (%p). send_message_payload_ == nullptr ssl_creds != nullptr client_secret grpc_compute_engine_credentials_create(reserved=%p) pem_root_certs != nullptr fopen Verify peer callback returned a failure (%d) G:\PES22HC\Dev-600Series\Source\Shared\basic\ext\grpc\grpc\src\core\tsi\alts\handshaker\transport_security_common_api.cc metadata.google.internal.:8080 self != nullptr G:\PES22HC\Dev-600Series\Source\Shared\basic\ext\grpc\grpc\src\core\tsi\alts\frame_protector\frame_handler.cc call_error == GRPC_CALL_OK GRPC_XDS_BOOTSTRAP errors parsing xds

OFFSET=0xb6a2b1 TERM=turn
CONTEXT=th an existing enum type. CHECK failed: options_descriptor: " was already set. CHECK failed: uninterpreted_options_field != NULL: MapValueRef::GetDoubleValue Message does not support reflection (type Extension factory's GetPrototype() returned NULL for extension: Unknown enumeration value of " "e" must be followed by exponent. GRAPHICSTRING d=%-2d hl=%ld l=inf NIST/SECG curve over a 224 bit prime field X9.62/SECG curve over a 256 bit prime field NIST/SECG curve over a 571 bit binary field RFC 5639 curve over a 384 bit prime field DH Public-Key Field Type: %s OpenSSL X25519 algorithm BN_div_

OFFSET=0xb6cce6 TERM=turn
CONTEXT= AVG_LOWERCASE_WIDTH DEVICE_FONT_NAME END_SPACE RAW_MAX_SPACE RAW_SMALL_CAP_SIZE RAW_SUPERSCRIPT_SIZE UNDERLINE_POSITION SWIDTH XUID ExpertEncoding mn- und-Syre HB_SHAPER_LIST invalid chromaticities too short Interlace handling should be turned on when using png_read_image Read palette index exceeding num_palette png_image_finish_read: row_stride too large output gamma out of expected range Uninitialized row Not a PNG file invalid window size (libpng) zstream unclaimed png_set_gAMA Invalid format for pCAL parameter /proc/cpuinfo open failed virtual void swappy::ChoreographerThread::postFrameCall

OFFSET=0xb74d1f TERM=turn
CONTEXT=::CircularOut bHasRootMotion AnimNotifies LinkedAnimGraphNodeProperties TranslationCompressionFormat AllowedScaleFormats bResampleAnimation AACF_Editable RawCurveTracks OnMontageBlendingOutStartedMCDelegate__DelegateSignature EMontagePlayReturnType::Duration LockAIResources Montage_IsActive Montage_SetNextSection MachineIndex ReturnValueType InTimeToStartMontageAt EDrawDebugItemType::DirectionalArrow EDrawDebugItemType::CoordinateSystem AnimLinkableElement DisableRootMotionCount EPinHidingMode::AlwaysAsPin PlayRateBasis LinkToCachingNode BoneCompressionSettings ETAA_Looped AnimSetMeshLinkup SetBle

OFFSET=0xb74d79 TERM=turn
CONTEXT=sionFormat AllowedScaleFormats bResampleAnimation AACF_Editable RawCurveTracks OnMontageBlendingOutStartedMCDelegate__DelegateSignature EMontagePlayReturnType::Duration LockAIResources Montage_IsActive Montage_SetNextSection MachineIndex ReturnValueType InTimeToStartMontageAt EDrawDebugItemType::DirectionalArrow EDrawDebugItemType::CoordinateSystem AnimLinkableElement DisableRootMotionCount EPinHidingMode::AlwaysAsPin PlayRateBasis LinkToCachingNode BoneCompressionSettings ETAA_Looped AnimSetMeshLinkup SetBlendSpaceInput ETransitionLogicType::TLT_Inertialization CanTakeDelegateIndex AAT_None ETemp

OFFSET=0xb780e4 TERM=turn
CONTEXT=_090 kick_long_0_0_instep_y0_000 kick_long_0_0_instep_y2_000 kick_long_0_0_instep_y2_135 kick_long_3_0_instep_y1_090 kick_long_0_0_inside_y0_000_curve kick_mid_0_0_instep_y2_135_late kick_mid_4_0_inside_y0_f045 autoMove_40_circle_short_run_turn_2_2_bodyangle_keep kick_short_0_0_infront_y0_045 kick_short_0_0_inside_y4_f045 kick_short_3_0_inside_y0_090_far kick_short_3_0_outside_y0_000_lob kick_short_3_0_outside_y0_f045 kick_short_3_0_outside_y2_f045 kick_short_3_4_inside_y0_f045_r_045 layer_give_side_bothup lose_nutmeg_idle_0_0_180 lose_nutmeg_run_3_0_f270 stagger_upbody_2_3_045 tacklefoot_parallel

OFFSET=0xb786d0 TERM=turn
CONTEXT=ove_00_bodyangle_00_90_f90_00_2_2_mid autoMove_32_go_to_3m_3m_parallel_to_reverse_act099 js_run_2_2_000_guard_side_set007_of_act068 block_0_0_y00_f090_kneedown_look_f090 js_run_3m_3m_000_guard_side_set016_pulled_of_act097 gkmovenear_idlemidturn_135 gkmovenear_sidestep_0_3_1_short autoMove_01_reverse_loop_front_back_1_1_mid kick_long_3_0_instep_y0_000_curve kick_mid_0_0_inside_y0_000_late js_run_3_3_000_guard_side_set005_df_win_act064 dm_oop_gk_idle_0_0_idle_mortfying_06 js_run_3_3_000_push_away_hard_v2 pk_idle_ronaldinho_2 autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_STEP_mid autoMove_11_bo

OFFSET=0xb78816 TERM=turn
CONTEXT=ick_long_3_0_instep_y0_000_curve kick_mid_0_0_inside_y0_000_late js_run_3_3_000_guard_side_set005_df_win_act064 dm_oop_gk_idle_0_0_idle_mortfying_06 js_run_3_3_000_push_away_hard_v2 pk_idle_ronaldinho_2 autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_STEP_mid autoMove_11_bodyangle_rolling_slow_2_2_mid dm_oop_calmdown_000_idle autoMove_00_bodyangle_00_90_f90_00_2_2_near autoMove_01_dribble_reverse_loop_front_back_3_3_mid_gabriel BallBoy_pickup autoMove_01_reverse_loop_slant_backslant_2_2_near autoMove_30_dribble_turn_move_3_3_CIRCLE_mid_gabriel autoMove_30_turn_move_3_3_CRANK_mid_michael autoMo

OFFSET=0xb7892f TERM=turn
CONTEXT=ngle_rolling_slow_2_2_mid dm_oop_calmdown_000_idle autoMove_00_bodyangle_00_90_f90_00_2_2_near autoMove_01_dribble_reverse_loop_front_back_3_3_mid_gabriel BallBoy_pickup autoMove_01_reverse_loop_slant_backslant_2_2_near autoMove_30_dribble_turn_move_3_3_CIRCLE_mid_gabriel autoMove_30_turn_move_3_3_CRANK_mid_michael autoMove_05_dribbel_zigzag135_front_loop_3_3_mid_gabriel autoMove_08_dribble_ragged45_slant_loop_3_3_mid_gabriel Slower_0_3_090 autoMove_02_reverse_stop_leftside_rightside_3_3_STEP_near_gabriel autoMove_06_zigzag135_side_loop_3_3_near_gabriel dash_08_dash_4_0_090_neardelay_Oriul dash_10

OFFSET=0xb7895c TERM=turn
CONTEXT=_idle autoMove_00_bodyangle_00_90_f90_00_2_2_near autoMove_01_dribble_reverse_loop_front_back_3_3_mid_gabriel BallBoy_pickup autoMove_01_reverse_loop_slant_backslant_2_2_near autoMove_30_dribble_turn_move_3_3_CIRCLE_mid_gabriel autoMove_30_turn_move_3_3_CRANK_mid_michael autoMove_05_dribbel_zigzag135_front_loop_3_3_mid_gabriel autoMove_08_dribble_ragged45_slant_loop_3_3_mid_gabriel Slower_0_3_090 autoMove_02_reverse_stop_leftside_rightside_3_3_STEP_near_gabriel autoMove_06_zigzag135_side_loop_3_3_near_gabriel dash_08_dash_4_0_090_neardelay_Oriul dash_10_walk_1_4_045_dash_Oriul nearDefense_04_BODYT

OFFSET=0xb78c84 TERM=turn
CONTEXT=_sole_in_act097 dm_oop_pointing_f090_parallel_2_1_side_000 dm_oop_pointing_f135_parallel_2_2_parallel_000 gkFumble_f00_0_0_y06 dml_goal_celebrate_0087 kick_long_3_0_instep_y0_090_pirlo StabilizerCam_idle_0_1_walkside_R StabilizerCam_corner_turn_2_R StabilizerCam_walkside_1_1_R dm_oop_pointing_f135_idle_0_0 dm_oop_pointing_f135_run_2_2 dml_goal_celebrate_0144 F_ActualBattle_191007_F011_t02_Gabriel_Fcut002 F_ActualBattle_191008_FZ006_t01_Jhoan_Fcut004 F_ActualBattle_200127_F025_t01_Ortega_Fcut007 LongVersion_161104_F026_t01_Mobi_02 enum_dummy30 enum_dummy34 new_dribblerun_3_3_s_f045_out dribblerun_3

OFFSET=0xb7a39e TERM=turn
CONTEXT= demo_coop_goodJob demo_coop_touchHigh dm_oop_faceup_0_0_idle_protest_hard demo_goal_recorder puntkick_side_0_0_nearline_cancel throw_over_3_0_high judge_point_to_1_low judge_fk_indirect_start kickoff_loop_tired_mild2 linesman_2_2 linesman_turn_2_2_run seamless_pass_direct blockfront_2_0_y01_shoot_reaction_v3 blockfront_2_0_y04_shoot_reaction_v3 fall_lowbody_2_0_l stagger_lowbody_0_0_hard_r stagger_upbody_2_2_v2 stagger_ballhit_belly_0_0 demo_move_tired_nose kickfeint_valdivia_4_3_r demo_miss_0_1_hip_090_1 demo_miss_3_1_hip_090_2 demo_gk_miss_6 demo_gk_miss_fallside_1 demo_droop_hurry_4 demo_droop

OFFSET=0xb7baf4 TERM=turn
CONTEXT=ISION CmdDeleteRoomGuest.php CmdGetRequestedJoinRoomInfo.php enable_room_entry_restriction CmdSetRoomUserSquadEnable.php CmdUnsetRoomMatchReady.php CmdDeleteMyclubSquad.php CmdGetLoginBonusInfo.php gameplayer_sell_gp CmdGetSeasonInfo.php return_myleague_point CmdKickUserCompe.php CMD_SET_USER_COMPE_TEAM_ID pk_score CMD_GET_IS_KID_ACCOUNT_LINK CmdGetIsKidAccountLinkForRestart.php Coin_04 IsCompleteDestroySession G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineMode\Multiplay\OnlineModeMultiplay.cpp CompetitionEventListInfoWork %012llu ImpactPassCross CgkI2KWEy_UIEAIQUg TaskMlEventMainMe

OFFSET=0xb83760 TERM=turn
CONTEXT=Agent_C /Game/Assets/ui/Data/Widget/General/List/ManagerList/ManagerList.ManagerList_C EndFadeOut %s call. move to (%f, %f) LoadedCompeLogo Tex1080/ Wide [%s], isEnable:%d %s is waiting for ending [Vip]already, CloseImpl %s FrameOutReturn bIsIncludeUserWidget ResourceTables_Key EPreLoadingType::Max WidgetPtr EAudiType2::Type_Away BoundSize OffsetPosIRanges TeamFloorAttendances ReduceAreaPlacementInfos GetAudiType EAutoPilotNextSequenceType::Footer target DefaultMed MinMed ECharacterPartsType::Tights ActivePlayerList MemberId ResetLoadingStep Rot UseEmblem AccessoryDatas Glove OnSpawnedMontag

OFFSET=0xb86f2f TERM=turn
CONTEXT=vice, &BufferCreateInfo, VULKAN_CPU_ALLOCATOR, &CpuReadbackBuffer->Buffer) LoadLocalizedResourcesFromPaths Commandline UInt16Property SetProperty EnumProperty Aniso execTracepoint execAddMulticastDelegate execUInt64Const execMapConst EAppReturnType::No EUnit::Pounds EUnit::Gigabytes EMouseCursor::EyeDropper PF_Unknown PF_G16R16 CIM_CurveAuto EAxis Timestamp AutomationEvent AxisX Five O Gamepad_DPad_Left Global_Back OculusTouch_Right_Thumbstick_Down ValveIndex_Right_Trackpad_Y ValveIndex_Right_Trackpad_Touch ETouchIndex::Touch6 isPlaying setDataSource com/epicgames/ue4/MediaPlayer14$FrameUpdateInfo

OFFSET=0xb8bba5 TERM=turn
CONTEXT=ar_sliding dm_oop_gk_idle_0_1_walkCool_045 dm_oop_gk_riseup_0_1_sideways_withGuts_045 gkdeflect_f02_back_3_0_y10_090 sliding_0_0_f045 js_run_2_2_135_guard_passget_act068_v2 gkseeoff_front_react_3_1_y05 tacklefoot_mid_0_0_f067_block throwin_turn_067_loop trapback_3_0_000_y6_breast_fast traprun_3_3_f045_y2_in traprun_3_3_s_000_y0_mid_in traprun_3_3_s_000_y2_in_ver12 traprun_3_3_s_000_y8_breast traprun_3_3_s_022_y0_in_axisback_ver2 traprun_3_3_s_f011_y1_out_near_ver12 traprun_4_4_s_000_y4_mid_out traprun_4_4_s_000_y6_far_in traprun_boundball_3_3_s_000_y4_near_breast_ver03 trap_0_0_f045_y2_out_boundba

OFFSET=0xb8c007 TERM=turn
CONTEXT=0_axisback_in_act097 autoMove_00_bodyangle_00_90_f90_00_3_3_STEP_mid gkmovenear_front_3_3_090 kick_mid_3_0_infront_y0_045_punch fall_upbody_3_0_090_jostle_push_lose stagger_upbody_3_3_090_interrupt_lose_v2 autoMove_01_reverse_loop_parallel_turn_2_2_mid autoMove_06_zigzag135_side_loop_3_3_STEP_mid dm_oop_linekeep_f180_mid_delay dm_oop_pass_point_f045_run_3_3_f045 dash_04_turn_4_4_045_CIRCLE_Ortega autoMove_04_crank45_loop_2_2_STEP_near autoMove_04_crank45_loop_3_3_STEP_mid_michael avoidslide_0_3_000_push_aside_act080_01 avoidslide_0_3_000_push_aside_act084_01 autoMove_02_reverse_stop_front_back_1_1

OFFSET=0xb8c08c TERM=turn
CONTEXT=upbody_3_0_090_jostle_push_lose stagger_upbody_3_3_090_interrupt_lose_v2 autoMove_01_reverse_loop_parallel_turn_2_2_mid autoMove_06_zigzag135_side_loop_3_3_STEP_mid dm_oop_linekeep_f180_mid_delay dm_oop_pass_point_f045_run_3_3_f045 dash_04_turn_4_4_045_CIRCLE_Ortega autoMove_04_crank45_loop_2_2_STEP_near autoMove_04_crank45_loop_3_3_STEP_mid_michael avoidslide_0_3_000_push_aside_act080_01 avoidslide_0_3_000_push_aside_act084_01 autoMove_02_reverse_stop_front_back_1_1_STEP_near_gabriel autoMove_00_bodyangle_00_90_00_3_3_near_gabriel avoidslide_2_4_000_rapid_low_push_aside_act068_01 autoMove_33_IDLE

OFFSET=0xb8c9c8 TERM=turn
CONTEXT=w_dribbleslide090_3_4_f090_y0_out_ver21 LongVersion_200127_F002_t02_Gabriel LongVersion_200127_F004_t01_Oriul LongVersion_200127_F005_t01_Ortega enum_dummy235 enum_dummy243 enum_dummy275 enum_dummy279 autoMove_40_circle_short_neardelayside_turn_2_2_bodyangle_keep_act079 dash_03_loop_4_2_4_000_act068 dash_06_back_2_4_parallel_225_act068 dash_06_side_2_4_parallel_f045_act080 dash_06_side_2_4_run_f135_act080 enum_dummy294 dm_oop_droop_1_3_180_act071_01 enum_dummy305 enum_dummy315 enum_dummy322 LongVersion_201123_F027_t01_act068_03 LongVersion_201123_F030_t03_act071_02 LongVersion_201124_F033_t01_act0

OFFSET=0xb8cfab TERM=turn
CONTEXT=R_CONTACT HAND IsLevelSetVisible %s FadeListener Immediate connect fail for %s: %s closing connection #%ld a DoH request is completed, %u to go Unexpected TYPE Unexpected CLASS CONNECT start Proxy-authenticate: IPv4: %s The requested URL returned error: %d %s: %s, %02d %s %4d %02d:%02d:%02d GMT Malformed encoding found Bad content-encoding found Keep-Alive Nov %2ld:%02ld:%02ld Request completely sent off client_write(type=%x, len=%zu) -> %d read function returned funny value cr_in, rewind via fseek -> %d(%d) Excessive password length for proxy auth Could not resolve proxy name FTP: could not ret

OFFSET=0xb8d08a TERM=turn
CONTEXT= requested URL returned error: %d %s: %s, %02d %s %4d %02d:%02d:%02d GMT Malformed encoding found Bad content-encoding found Keep-Alive Nov %2ld:%02ld:%02ld Request completely sent off client_write(type=%x, len=%zu) -> %d read function returned funny value cr_in, rewind via fseek -> %d(%d) Excessive password length for proxy auth Could not resolve proxy name FTP: could not retrieve (RETR failed) the specified file Malformed option provided in a setopt RTSP CSeq mismatch or invalid CSeq An authentication function returned an error Malformed input to a URL function Bad user Connection died, retryi

OFFSET=0xb8d1a4 TERM=turn
CONTEXT= -> %d(%d) Excessive password length for proxy auth Could not resolve proxy name FTP: could not retrieve (RETR failed) the specified file Malformed option provided in a setopt RTSP CSeq mismatch or invalid CSeq An authentication function returned an error Malformed input to a URL function Bad user Connection died, retrying a fresh connect (retry count: %d) Found pending candidate for reuse and CURLOPT_PIPEWAIT is set %s%s.netrc Error %d sending MQTT CONNECT request %u.%u.%u.%u 0123456789abcdefABCDEF:. public key hash: sha256//%s issuer: %s Next protocol Issuer %02x SSL: unable to obtain common n

OFFSET=0xb93777 TERM=turn
CONTEXT= criVdec_ReleaseFramePointer(). Thread-unsafe function has been executed in parallel. E2009072402:Can not change allocator. Allocated memory is still active. E2010042609:Server frequency has already been set. E2012040402:criServer Create return NULL. E2008070387 E2008070053:Lock cunter overflowed. SjRbfBuffer CriAu_new W2010071401:The target information(%d) of the ACF does not match. E2021121501:ACF file is not registered. E2017122223:ACF file is not registered. E2017122236:ACF file is not registered. E2021121722 W2019111222:Specified DSP parameter buffer size is not enough (in Surrounder DSP). W2

OFFSET=0xb96b13 TERM=turn
CONTEXT=/MenuUserCompeGroupStageDraw Settings/GameSettings/MenuDataDownload Settings/Support/MenuVoidCoachList [Header] %s (%s) /Game/Assets/ui/Data/Widget/Parts/Components/BG/SwitchBG_Original/BGAnime.BgAnime Clear Anim:%s (%s) MT\d+ FrameOutReturnEnd PlayMenuAnimation EPreLoadingUniqueID::Resident_UserWidget_DataTable EAudiType2::Type_Stand_AwayNormal EAudiArea::Area_Main1 MakePlacementInfo GetPlaneDir Floor3 MeshComponent OnReadyEditUniform SetCharacterConfigFaceType SetUniformConfigEditSocks SetUniformConfigPantsNumber longPosH m_cover_compo m_face_name BlendJawOpen m_stainMaskTex SetCursorDownText

OFFSET=0xb9a306 TERM=turn
CONTEXT=reateInfo, VULKAN_CPU_ALLOCATOR, &Image) clear FAndroidPlatformStackWalk::CaptureStackBackTrace disabled on Android 10 with TargetSDK >= 29 due to XOM. Super DGram InterpCurveTwoVectors execBreakpoint execInstrumentation execMetaCast EAppReturnType::Retry EUnit::Millimeters EMouseCursor::ResizeSouthEast PF_G16R16F_FILTER PF_BC7 ARFilter NativeString bIsMinimalPatch Scale3D MiddleMouseButton NumPadEight Equals Dollar Exclamation Gamepad_DPad_Up Gamepad_LeftStick_Down Daydream_Right_Trackpad_X ValveIndex_Left_Thumbstick_Right ValveIndex_Left_Trackpad_Down Gamepad \ ErrorReporting.EmptyBox VerticalBo

OFFSET=0xb9ef47 TERM=turn
CONTEXT=_win_act064 js_run_4_4_000_guard_side_set017_pushed_df_act064 feint_trap_lift_guardside_0_0_s_000_sidefar_y0_near_toe_ver16 trapback_boundball_3_0_000_y5_breast_ver21 feintrun_roulette_2_3_f067_y0_in_out_act099 autoMove_40_circle_short_run_turn_3_3_bodyangle_keep autoMove_05_zigzag135_front_loop_1_1_mid autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_v2_mid autoMove_40_circle_run_turn_2_2_mid autoMove_01_reverse_loop_front_back_2_2_mid_michale autoMove_05_dribble_zigzag135_front_loop_1_1_mid_gabriel head_y07_sidle_short_3_2_090_act064 coach_0_1_f090_normal_oop_glad_high gkdeflectscoop_f01_3_0_

OFFSET=0xb9efad TERM=turn
CONTEXT=far_y0_near_toe_ver16 trapback_boundball_3_0_000_y5_breast_ver21 feintrun_roulette_2_3_f067_y0_in_out_act099 autoMove_40_circle_short_run_turn_3_3_bodyangle_keep autoMove_05_zigzag135_front_loop_1_1_mid autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_v2_mid autoMove_40_circle_run_turn_2_2_mid autoMove_01_reverse_loop_front_back_2_2_mid_michale autoMove_05_dribble_zigzag135_front_loop_1_1_mid_gabriel head_y07_sidle_short_3_2_090_act064 coach_0_1_f090_normal_oop_glad_high gkdeflectscoop_f01_3_0_y02 autoMove_30_turn_move_1_1_CIRCLE_mid_michael autoMove_05_zigzag135_front_loop_3_3_STEP_near_gabrie

OFFSET=0xb9efda TERM=turn
CONTEXT=000_y5_breast_ver21 feintrun_roulette_2_3_f067_y0_in_out_act099 autoMove_40_circle_short_run_turn_3_3_bodyangle_keep autoMove_05_zigzag135_front_loop_1_1_mid autoMove_10_bodyangle_keep_circle_bigturn_front_3_3_v2_mid autoMove_40_circle_run_turn_2_2_mid autoMove_01_reverse_loop_front_back_2_2_mid_michale autoMove_05_dribble_zigzag135_front_loop_1_1_mid_gabriel head_y07_sidle_short_3_2_090_act064 coach_0_1_f090_normal_oop_glad_high gkdeflectscoop_f01_3_0_y02 autoMove_30_turn_move_1_1_CIRCLE_mid_michael autoMove_05_zigzag135_front_loop_3_3_STEP_near_gabriel avoidslide_2_4_000_push_aside_act068_01 aut

OFFSET=0xb9f0c3 TERM=turn
CONTEXT=le_run_turn_2_2_mid autoMove_01_reverse_loop_front_back_2_2_mid_michale autoMove_05_dribble_zigzag135_front_loop_1_1_mid_gabriel head_y07_sidle_short_3_2_090_act064 coach_0_1_f090_normal_oop_glad_high gkdeflectscoop_f01_3_0_y02 autoMove_30_turn_move_1_1_CIRCLE_mid_michael autoMove_05_zigzag135_front_loop_3_3_STEP_near_gabriel avoidslide_2_4_000_push_aside_act068_01 autoMove_05_dribble_zigzag135_front_loop_3_3_STEP_near_gabriel autoMove_32_dribble_go_to_2_2_near_gabriel dash_01_loop_4_4_Oriul dash_09_idle_0_4_000_dash_Oriul dash_10_side_1_4_f270_dash_Oriul moveAdjust_05_Side_1_1_gabriel nearDribble

OFFSET=0xb9f884 TERM=turn
CONTEXT=ongVersion_200127_F002_t01_Takayama LongVersion_200127_F002_t02_Ortega enum_dummy193 enum_dummy218 enum_dummy254 enum_dummy260 enum_dummy265 gkgoalkick_inside_mid_0_0_f090 enum_dummy282 dml_goal_celebrate_0241 autoMove_40_circle_short_side_turn_3_3_bodyangle_keep_act080 dash_06_back_2_4_parallel_090_act068 dash_06_slant_2_4_parallel_f045_act068 js_run_4_3_045_holdmiss_act068 dm_oop_gk_riseup_0_0_sideways_walkGuts_000_v02 dm_oop_angry_1_3_090_act071_02 dm_oop_appeal_3_3_180_at045_act071 enum_dummy340 enum_dummy352 LongVersion_201123_F027_t01_act068_02 LongVersion_201123_F028_t01_act071_01 enum_dumm

OFFSET=0xb9fb50 TERM=turn
CONTEXT=dummy479 enum_dummy484 enum_dummy539 enum_dummy558 enum_dummy559 ShortVersion_201123_F001_t01_act068_02 enum_dummy612 enum_dummy625 enum_dummy634 defenseMove_01_parallel_3_4_run_act068 passGetMove_01_run_3_3_side_f180_act068 gkmovenear_stopturn_2_0 base_d_end_photo_hey cry_brwnit_lorol_eyc ef23_purse_one_lips_small ef23_shout_loop_close_eye gk_brwnit_shut gk_puck neut_bite_soft_slow neut_breath_short_shoot_S_02 neut_brwup_talk_eyo neut_deep neut_long neut_song_01 neut_talk_03 pain_brwnit_wide_eyc pose_smile_L_01 pose_sorrow_dejection_S_03 pose_sorrow_pain_shout_03 pose_sorrow_surprise_M_01 pow_brw

OFFSET=0xba024d TERM=turn
CONTEXT=n/match/constant/ballPerson/ball_person_st102.json DevelopData/common/match/constant/pathToGlory/PathToGlory1.json DevelopData/common/match/constant/positionPK/positionNone.json DevelopData/common/match/constant/stadium/demoarea_st026.json turnAngleStart debugKickSpeed overRotMin topSpinChangeSpeed movetime coef_df_1on1 subValue10percent distMax kickPowerParameter version floatValue09 pauseRestartMoveSpeed p0_length_mle distMin_high passAssistLevel distRate angleY dist footPosWeight headPosWeight ballAngle moveRangeFree playerOffence gageMin angleRateMaxFly gageTest5 passgetMoveLateFrame searchLen

OFFSET=0xba074a TERM=turn
CONTEXT=ble/bin/CategorizedMoveTableStatus.bin cpk_dat/common/anime/AnimeTable/bin/OOPDemoData.bin camera_person_move_side_2_2 demo_pfm_jumpunderguts_3_3_r dm_oop_facedown_0_0_idle_protest demo_goal_archer_loop throw_over_3_0_hard2_cancel linesman_turn_0_3 seamless_run_setup_3_0 blockfront_0_0_y00_shoot_near blockfront_2_0_y00_shoot_reaction fall_lowbody_2_0_sliding_high_r stagger_lowbody_0_0_hard_l goalturn_pointing_backAssist goalturn_powershot demo_move_3_1_135_step demo_glad_3_1_135 demo_miss_0_1_droop_045_1 demo_miss_3_0_allfours_135 demo_gk_miss_3 demo_gk_miss_9 demo_droop_hurry_11 demo_appeal_0_1_a

OFFSET=0xba07e9 TERM=turn
CONTEXT=down_0_0_idle_protest demo_goal_archer_loop throw_over_3_0_hard2_cancel linesman_turn_0_3 seamless_run_setup_3_0 blockfront_0_0_y00_shoot_near blockfront_2_0_y00_shoot_reaction fall_lowbody_2_0_sliding_high_r stagger_lowbody_0_0_hard_l goalturn_pointing_backAssist goalturn_powershot demo_move_3_1_135_step demo_glad_3_1_135 demo_miss_0_1_droop_045_1 demo_miss_3_0_allfours_135 demo_gk_miss_3 demo_gk_miss_9 demo_droop_hurry_11 demo_appeal_0_1_at045_4 demo_appeal_hurry_5 demo_praise_hurry_2 TimeUp_0_1_Droop_1_2 HalfEnd_1_1_Tired dodge_human_jumplow_2 dodge_human_slide_rapid_down_3_3 bodyfake000_4_4_r 

OFFSET=0xba0806 TERM=turn
CONTEXT=al_archer_loop throw_over_3_0_hard2_cancel linesman_turn_0_3 seamless_run_setup_3_0 blockfront_0_0_y00_shoot_near blockfront_2_0_y00_shoot_reaction fall_lowbody_2_0_sliding_high_r stagger_lowbody_0_0_hard_l goalturn_pointing_backAssist goalturn_powershot demo_move_3_1_135_step demo_glad_3_1_135 demo_miss_0_1_droop_045_1 demo_miss_3_0_allfours_135 demo_gk_miss_3 demo_gk_miss_9 demo_droop_hurry_11 demo_appeal_0_1_at045_4 demo_appeal_hurry_5 demo_praise_hurry_2 TimeUp_0_1_Droop_1_2 HalfEnd_1_1_Tired dodge_human_jumplow_2 dodge_human_slide_rapid_down_3_3 bodyfake000_4_4_r trapside_l_3_3_y0_in_fangle3 

OFFSET=0xba419f TERM=turn
CONTEXT=, %s data_allocated_size is smaller than sum of data_size and num_overhead_bytes. get_serialized_next() failed Could not write into openssl BIO. (uintptr_t)(current - result) == result_len Invalid handshake message. tsi_fake_frame_decode returned %s failed to parse bootstrap file JSON duplicate "type" field [xdslb %p] Locality %p %s: failure creating child policy %s old_state != GRPC_CHANNEL_SHUTDOWN ). Contact the program author for an update. If you compiled the program yourself, make sure that your headers are from the same version of Protocol Buffers as your link-time library. (Version veri

OFFSET=0xba43b2 TERM=turn
CONTEXT=ame version of Protocol Buffers as your link-time library. (Version verification failed in " G:\PES22HC\Dev-600Series\Source\Shared\basic\ext\grpc\grpc\third_party\protobuf\src\google\protobuf\io\strtod.cc CHECK failed: (count) <= (last_returned_size_): double int64 " is resolved to " Message extensions cannot have required fields. Extension range end number must be greater than start number. " must be unique within "$0" does not declare $1 as an extension number. [lazy = true] can only be specified for submessage fields. google/protobuf/descriptor.proto Protocol Buffer map usage error: MapVal

OFFSET=0xba5351 TERM=turn
CONTEXT=_ems tls_parse_ctos_key_share tls_process_certificate_request tls_process_cke_ecdhe tls_process_key_update bad srtp protection profile list dane tlsa bad public key missing supported groups extension old session compression algorithm not returned sslv3 alert decompression failure ssl session version mismatch unexpected ccs message unsafe legacy renegotiation disabled ClientCAPath SSLv3/TLS read client key exchange TRSKU TPEDE export restriction user canceled rsa_pkcs1_sha1 Intro/ProcessIntroInputUserInfo Match/Setup/MatchDirectTutorialSetup Match/Sugoroku/SugorokuSetting Match/Sugoroku/SugorokuPla

OFFSET=0xba5641 TERM=turn
CONTEXT=nline/Lobby/ProcLobbyRoomGoMatch Online/EvCompe/PresetCoop/ProcEvCompeEventInit Online/EvCompe/RecordEvent/ProcEvCompeEventInit Online/EvCompe/StrikeArena/ProcEvCompeEventEnter postOnlineMatch path_to_glory_failure_dialog coop_vs_in_room return_error matching_strike_arena memberNum initialNationalTeamId customizePoint G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Process\Online\Matching\ProcessOnlineMatchingInit.cpp SaveDataWorkerThread CA_REPLAY_ROOT SA_C_NMB_E26 SA_C_NMB_E44 SA_C_NMB_E47 SA_C_NMB_E59 SA_C_NMB63 cpk_snd/common/sound/config/ConvertList.bin standalone="%s" ?> <%s> A1_TCT Connect

OFFSET=0xba920b TERM=turn
CONTEXT=rVector EBoneForwardAxis::Z_Positive bInitPhysicsSettings WorldVerticalStrength RegexPatternBone2 Guid ERequestType::RT_Stop PesSoundSystemSampleFunction EAtomAudioVolumeType::UseSnapshot bSwitchIntepolationInsideForAisac EntranceVolumes ReturnValue_Key DefaultVolume Snapshot CategoryCuePriorityTypeIndex Blocks AtomListenerFocusPointInfo ConcurrencyName AtomTriggerRow OnWavePlaybackPercent__DelegateSignature StopDelayed SetGameVariableByName PS4_ServerThreadAffinityMask FrameNumber ChangeSubtitlesEncoding RemoveAudioCategory RemoveExtraAudioCategory EManaComponentTextureType::Texture_UV EManaCompo

OFFSET=0xbac0f7 TERM=turn
CONTEXT=nd::SideSettingView ELobbyRoomAlertKind::SelectSetting IsStrikeArenaMultiRoom OpenSendMessageView IsForPadevent ELayoutMatchMainMenuCoopUserRequest::Away DesiredSideStr DesiredSidePtr BonusValueStr ELayoutStrikeArenaCoopUserInfo::Ready IsReturnedSquadDisable ELobbyRoomMatchSettingsItem::MATCH_RULE ELobbyRoomMatchSettingsItem::EX ELobbySideSelectSideAnime::SetAway ELobbySideSelectSideAnime::MoveCenterToHome ELobbySideSelectUserCellSide::Home EMenuMailboxCommandResult::COMMAND_RESULT_NONE fstrTitle SetupExitSpectateAlertDialog m_userCompeEmojiList OnReleasedSaveLoadButton CheckPadEventAnyKey EMenuMa

OFFSET=0xbb0385 TERM=turn
CONTEXT=_Int64Int64 Quat_Log Quat_MakeFromEuler Vector_Backward Vector_BoundedToCube Vector_Normalize FractionNano InUseSRGB bRoll InPlane ClearAllBits EndDrawCanvasToRenderTarget ReadRenderTargetRawPixel Conv_StringToFloat EMoveComponentAction::Return EMoveComponentAction CanLaunchURL DrawDebugArrow ForceCloseAdBanner GetSoftClassReferenceFromPrimaryAssetId GetVolumeButtonsHandledBySystem K2_ClearAndInvalidateTimerHandle K2_IsValidTimerHandle K2_SetTimer RegisterForRemoteNotifications SetCollisionProfileNameProperty AngleWidth OutPrimaryAssetIdList EFormatArgumentType::Gender EFormatArgumentType EFormatA

OFFSET=0xbb2bd3 TERM=turn
CONTEXT=ct064 kick_long_3_3_adjust_y0_000_sidle dm_oop_gk_riseup_sidewaysmid_l_0_2_f090 feintrun_stepkick_meialua_2_3_f067_y0_ver12 dribble_0_3_slide_f045_out_ver7 blockhead_0_0_y04_f090_near_down sliding_2_0_045_parallel_R passGetMove_03_parallel_turn_3m_3m_045_act064_v2 dm_miss_idle_0_1_walk_droop_045_3 dm_miss_idle_0_1_walk_head_045_2 autoMove_00_bodyangle_00_90_f90_00_3_3_mid block_0_0_y03_000_near_thigh_bend_backward block_2_0_y04_000_look_270 kick_long_2_2_adjust_y0_000 head_y09_0_0_000_side_shed kick_long_3_0_infront_y0_000_curve kick_mid_0_0_toe_y0_000 autoMove_01_reverse_loop_parallel_back_3_3_mi

OFFSET=0xbb2eb9 TERM=turn
CONTEXT=0_run_2_3_000 dm_oop_pass_point_f045_run_2_3_f045 autoMove_03_dribble_crank90_loop_2_2_mid_gabriel autoMove_05_dribble_zigzag135_front_loop_2_2_mid_gabriel autoMove_05_zigzag135_front_loop_2_2_STEP_near autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_near autoMove_11_dribble_bodyangle_rolling_fast_2_2_mid_gabriel Freekick_Cancel head_y09_jostle_s_0_0_180_act064 autoMove_30_turn_move_1_1_CRANK_mid_michael autoMove_03_dribble_crank90_loop_3_3_mid_gabriel feintrun_bodyfake_front_3_3_000_y0_hard_ver20 autoMove_01_reverse_loop_side_2_2_STEP_near_gabriel autoMove_02_reverse_stop_front_back_3_3_near_

OFFSET=0xbb2f45 TERM=turn
CONTEXT=2_2_mid_gabriel autoMove_05_zigzag135_front_loop_2_2_STEP_near autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_near autoMove_11_dribble_bodyangle_rolling_fast_2_2_mid_gabriel Freekick_Cancel head_y09_jostle_s_0_0_180_act064 autoMove_30_turn_move_1_1_CRANK_mid_michael autoMove_03_dribble_crank90_loop_3_3_mid_gabriel feintrun_bodyfake_front_3_3_000_y0_hard_ver20 autoMove_01_reverse_loop_side_2_2_STEP_near_gabriel autoMove_02_reverse_stop_front_back_3_3_near_gabriel autoMove_04_dribble_crank45_loop_3_3_STEP_near_gabriel autoMove_32_go_to_1_1_near_gabriel dash_10_side_1_4_090_dash_Oriul moveAdjust

OFFSET=0xbb481e TERM=turn
CONTEXT=amMax lookAt topSpinRot floatValue10 intValue01 kind1 frame_max adjustSpeedGrounder debugDisp limitBackX gageMax searchMaxDistFly useSinCurveAngleY ballControlRate frameShortMax angleSub groundBall ballSideMaxRate_stratagy_defensive checkReturnDistZ keepDfTargetLineX slowDownMySide #Win/ cpk_dat/common/demo/fixdemo/setplay/table_setplay.bin LoadLevelSet %d %s None %s UnloadLevelSet %d Def_Game_System_Disp_ProcessLoad__OFF AddFlow flow::FlowTransition::MAIN_STEP_FLOW_FADEINSTART_WAIT STATE_BIND_PARENT fadeStart acl_low primeira_liga BALL_PERSON =player Part= DEMOPART_GOAL_PLAYER RetryAuto_PK_SPA_C

OFFSET=0xbb4c17 TERM=turn
CONTEXT=_0 seamless_goalkick_quick_short_l seamless_pull_ball_foot_3_0 blockfront_0_0_y03_shoot_near blockfront_2_0_y01_shoot_reaction blockside_2_0_y00 goalkick_seamless_idle_r fall_upbody_0_0_carry stagger_upbody_0_0_hard stagger_ballhit_0_0 goalturn_crawl_0_4 demo_move_tired_045_1 demo_move_1_0_side demo_glad_1_1_000_2 demo_angry_0_1_045_2 demo_angry_3_1_135_2 demo_gk_angry_lie_7 demo_miss_3_0_handOnKnee demo_miss_1_1_side_droop demo_droop_hurry_13 demo_appeal_0_1_at045_3_pat_2 demo_appeal_hurry_12 demo_cheer_at090 demo_cheer_instruct_at090 demo_praise_0_3_at135 demo_goal_extra_loop_0001 dodge_human_ju

OFFSET=0xbb7dd7 TERM=turn
CONTEXT=ers invalid universalstring length non hex characters string too long module initialization error eckey_priv_decode ec_GF2m_simple_oct2point ec_pkey_check o2i_ECPublicKey pkey_ecd_ctrl pkey_ec_sign point arithmetic failure BIO_new lookup returned nothing DSO_merge dso already loaded async_start_func invalid pool size aes128-wrap aes192 ssl3-sha1 RSA-SHA1-2 hexseed pkcs7-signedData RSA-SHA des-ede3-cfb Netscape CA Policy Url BF-CBC bf-cbc surname id-smime-alg id-pkix1-explicit-88 id-mod-cmp id-mod-dvcs id-regCtrl-authenticator prime-field prime239v3 AES-192-OFB AES-256-ECB dNSDomain documentIdentif

OFFSET=0xbb8840 TERM=turn
CONTEXT=erver_flight tls_process_next_proto tls_process_ske_dhe bad decompression bad srp parameters cookie mismatch error in received cipher list missing rsa certificate too many key updates unknown state unsupported elliptic curve wrong cipher returned no_resumption_on_reneg client_sigalgs requestCAFile TWCH opaqueBlob rsa_pss_pss_sha384 CLIENT_EARLY_TRAFFIC_SECRET Exhibition/ProcessPostGamePlan Match/Gimmick/GimmickWelcomeDialogEnd Intro/ProcessIntroDecideMainUser Online/UserCompe/ProcUserCompePostMatch Settings/UserInfo/ProcessUserDetailCommon opening_demo postMatchingTraining path_to_glory_clear gimm

OFFSET=0xbb924d TERM=turn
CONTEXT=Node *, N = 8] reinterpret_cast<size_t>(ptr) % RequiredAlignment == 0 unspecified generic_category error %.0Lf ctype_byname<char>::ctype_byname failed to construct for Unknown error type cntrl upper Particle fluid initialization failed: returned NULL. static const char *physx::shdfnd::ReflectionAllocator<physx::NpPtrTableStorageManager::PtrBlock<16> >::getName() [T = physx::NpPtrTableStorageManager::PtrBlock<16>] static const char *physx::shdfnd::ReflectionAllocator<physx::NpParticleSystem>::getName() [T = physx::NpParticleSystem] PxConstraint: Add to rigid actor 1: Constraint already added PxRig

OFFSET=0xbbaa83 TERM=turn
CONTEXT=052711M CriVmpv: HnObj IDCPREC CRIDLG_GetStat() is not supported on CRI Base2 Library. E2006120702 E2015021901M (Landroid/graphics/SurfaceTexture;)V E2022040404:Failed to setup H.264 Decode module. E2020082734 E2019100603:criCond Create return NULL. %d is exeeded . E2017122205:ACF file is not registered. E2017122215:ACF file is not registered. W2010110103:ACF file is not registered. E2012092701:ACF file is not registered. CRIWARE/Matrix W2013122000:This cue(id:%d) need selector information. Please set selector information to player. E2012020811 W2019073105:No voice pool uses specified instrument

OFFSET=0xbbee3c TERM=turn
CONTEXT=ubNarrowDownFilterKind Period CloseUnlockWarehouseOneTimeView DecideMlEventMatchLevelSelectCallbackEvent__DelegateSignature pWindow capturedTexture CallbackSetRevealedCardCmd CallbackClosedEditUserBanner EMenuTopMatchInitStep::End OnCloseReturnCoinAlertPopup OnLoginBonusPopupViewEnd EUserNameEditResult::Empty CallbackCompeNameTextCommittedEmpty InDropedItemPanel currentGroup EPromotionContentsRestrictionReason::Age GetJumpButtonStrForPaymentStore onReturnClose ECmnIconRewardType::TYPE_PLAYER ECmnIconRewardType::TYPE_RANDOM ECmnIconRewardType::TYPE_NUM EPresentReason::PRESENT_REASON_RECORD_EVENT_TI

OFFSET=0xbbef13 TERM=turn
CONTEXT=chInitStep::End OnCloseReturnCoinAlertPopup OnLoginBonusPopupViewEnd EUserNameEditResult::Empty CallbackCompeNameTextCommittedEmpty InDropedItemPanel currentGroup EPromotionContentsRestrictionReason::Age GetJumpButtonStrForPaymentStore onReturnClose ECmnIconRewardType::TYPE_PLAYER ECmnIconRewardType::TYPE_RANDOM ECmnIconRewardType::TYPE_NUM EPresentReason::PRESENT_REASON_RECORD_EVENT_TIME EPresentReason::PRESENT_REASON_COIN_BUNDLED_ITEM EPresentReason::PRESENT_REASON_REDEEM_CODE EPresentType::PRESENT_TYPE_E_FOOTBALL_POINT TextNum CmnRewardBreakdownDispInfo AvatarInfo EPosition::POSITION_LSB EPosit

OFFSET=0xbc1240 TERM=turn
CONTEXT=EngineTextLocalization ArrayProperty IntPoint Pointer ScriptStruct OtherChildren BeaconPort UnGrouped Warning Lerp QueuedPackagesQueueDepth StringClassReference execVirtualFunction execTextConst execSetMap bJoinViaPresenceFriendsOnly EAppReturnType::NoAll EMouseCursor::Default PF_R5G6B5_UNORM ELogTimes::Local OutVal ArriveTangent F2 F11 RightAlt Gamepad_Right2D Gamepad_Special_Left_X MixedReality_Right_Trackpad_X OculusTouch_Left_Menu_Click OculusTouch_Left_Trigger_Touch OculusTouch_Left_Thumbstick_Left OculusTouch_Right_System_Click OculusTouch_Right_Trigger_Axis OculusTouch_Right_Thumbstick_X Va

OFFSET=0xbc64ff TERM=turn
CONTEXT=_mid coach_0_0_000_hands_waist_inspire coach_0_1_090_cross_arms dm_oop_beckon_f135_mid_delay autoMove_05_zigzag135_front_loop_3_3_mid_michael autoMove_06_zigzag135_side_loop_3_3_STEP_mid_michael autoMove_10_dribble_bodyangle_keep_circle_bigturn_front_3_3_mid_gabriel dml_goal_celebrate_0341 Liftupcatch_0_0_y5 Liftup_passcatch_0_0_y5_ver2 Slowerrun_3_0_180 avoidjumpsliding_3_4_000_act068_03 autoMove_02_reverse_stop_leftside_rightside_1_1_STEP_near_gabriel dm_goal_extra_loop_0002 autoMove_00_bodyangle_00_135_00_1_1_STEP_near_gabriel autoMove_00_dribble_bodyangle_00_180_00_3_3_STEP_near_gabriel autoMo

OFFSET=0xbc66f6 TERM=turn
CONTEXT=_00_135_00_1_1_STEP_near_gabriel autoMove_00_dribble_bodyangle_00_180_00_3_3_STEP_near_gabriel autoMove_06_dribble_zigzag135_side_loop_1_1_STEP_near_gabriel autoMove_08_dribble__ragged45_slant_loop_3_3_STEP_near_gabriel autoMove_30_dribble_turn_move_3_3_CRANK_near_gabriel dash_07_dash_4_1_walk_Oriul dash_10_side_1_4_135_dash_Oriul tacklefoot_parallel_mid_2_0_000_act100 reaction_overtaken_3_3_180_stagger_short_act064 dm_oop_pointing_045_walk_1_2_run_135 dml_goal_celebrate_0105 dm_miss_sidestep_2_1_walk_angry_180 dm_oop_beckon_135_parallel_2_0_side_f090 gkcatch_f00_0_0_y10_hard tackleshoulder_3_2_in

OFFSET=0xbc7e37 TERM=turn
CONTEXT=e area ZONE_MF cpk_dat/common/anime/Mbinfo/bin/DangerData.bin [trap_through_check]dribble again [trap_through_check] adjust ok [lifttrap_check] adjust ok [trap]dummy balldist=%f, hitdist=%f [slidetrap_check] wait camera_person_corner_turn_2_2 camera_person_move_side_0_2 demo_handClap_1_1 demo_miss_angry_3_1_2 dm_oop_linekeep_walkslant_1_1 dm_oop_pointing_045_walk_1_2_run dm_miss_run_3_1_walk_angry_high_0 dm_miss_idle_0_1_walk_angry_high_1 demo_goal_archer linesman_throughin_left_hand linesman_turn_0_0 linesman_turn_0_2 seamless_catch_0_0_y6 seamless_catch_3_3_y5_v2 fall_air_lowbody_3_0 fall_

OFFSET=0xbc7f3f TERM=turn
CONTEXT=ove_side_0_2 demo_handClap_1_1 demo_miss_angry_3_1_2 dm_oop_linekeep_walkslant_1_1 dm_oop_pointing_045_walk_1_2_run dm_miss_run_3_1_walk_angry_high_0 dm_miss_idle_0_1_walk_angry_high_1 demo_goal_archer linesman_throughin_left_hand linesman_turn_0_0 linesman_turn_0_2 seamless_catch_0_0_y6 seamless_catch_3_3_y5_v2 fall_air_lowbody_3_0 fall_lowbody_4_0_v4_l goalturn_airplane_2_4 demo_normal_gk_2 kickfar_mid_4_0_inside_y0 demo_angry_3_1_135_1 demo_miss_0_1_head_045 demo_miss_3_1_head_135 demo_miss_3_1_hip_045 demo_droop_hurry_9 demo_appeal_hurry_10 demo_sorry_0_1_at135_2 demo_praise_hurry_4 dodge_huma

OFFSET=0xbc7f51 TERM=turn
CONTEXT=handClap_1_1 demo_miss_angry_3_1_2 dm_oop_linekeep_walkslant_1_1 dm_oop_pointing_045_walk_1_2_run dm_miss_run_3_1_walk_angry_high_0 dm_miss_idle_0_1_walk_angry_high_1 demo_goal_archer linesman_throughin_left_hand linesman_turn_0_0 linesman_turn_0_2 seamless_catch_0_0_y6 seamless_catch_3_3_y5_v2 fall_air_lowbody_3_0 fall_lowbody_4_0_v4_l goalturn_airplane_2_4 demo_normal_gk_2 kickfar_mid_4_0_inside_y0 demo_angry_3_1_135_1 demo_miss_0_1_head_045 demo_miss_3_1_head_135 demo_miss_3_1_hip_045 demo_droop_hurry_9 demo_appeal_hurry_10 demo_sorry_0_1_at135_2 demo_praise_hurry_4 dodge_human_decelerate_4_3_v

OFFSET=0xbc7fb8 TERM=turn
CONTEXT=ss_run_3_1_walk_angry_high_0 dm_miss_idle_0_1_walk_angry_high_1 demo_goal_archer linesman_throughin_left_hand linesman_turn_0_0 linesman_turn_0_2 seamless_catch_0_0_y6 seamless_catch_3_3_y5_v2 fall_air_lowbody_3_0 fall_lowbody_4_0_v4_l goalturn_airplane_2_4 demo_normal_gk_2 kickfar_mid_4_0_inside_y0 demo_angry_3_1_135_1 demo_miss_0_1_head_045 demo_miss_3_1_head_135 demo_miss_3_1_hip_045 demo_droop_hurry_9 demo_appeal_hurry_10 demo_sorry_0_1_at135_2 demo_praise_hurry_4 dodge_human_decelerate_4_3_v4 heellift_0_3_l kickfeint_3_3_y0_l rouletteribery_3_3_l scissorsout_3_3_l shakefootonce_0_0_l headside

OFFSET=0xbcbdb4 TERM=turn
CONTEXT=cEvCompeEventInit Online/EvCompe/MlEvent/Competition/ProcMlEventPreCompetitionMenu Online/League/ProcLeagueSkipDivision Online/UserCompe/ProcUserCompeCreate recordEventQuickGoalMainMenu path_to_glory_failure match_halftime stage_id gk_id return_squad_challenge return_tour levelCap SE_MATCHMAKING_IN_PROGRESS G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineMode\Task\Matching\OnlineModeTaskMatchingAndSession.cpp tutorial_match EL A1_BT1_01 SA_C_NMB_E10 SA_C_NMB_E52 Error parsing CDATA. ER A1_T3 A1_PPA PreArgs CheckDemoActionMoment CheckTime CheckBallTouchKindHistory CheckRemainingTimeNow

OFFSET=0xbcbdcb TERM=turn
CONTEXT=e/EvCompe/MlEvent/Competition/ProcMlEventPreCompetitionMenu Online/League/ProcLeagueSkipDivision Online/UserCompe/ProcUserCompeCreate recordEventQuickGoalMainMenu path_to_glory_failure match_halftime stage_id gk_id return_squad_challenge return_tour levelCap SE_MATCHMAKING_IN_PROGRESS G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineMode\Task\Matching\OnlineModeTaskMatchingAndSession.cpp tutorial_match EL A1_BT1_01 SA_C_NMB_E10 SA_C_NMB_E52 Error parsing CDATA. ER A1_T3 A1_PPA PreArgs CheckDemoActionMoment CheckTime CheckBallTouchKindHistory CheckRemainingTimeNowHalf CheckPlayerSkillId

OFFSET=0xbd72f0 TERM=turn
CONTEXT=sPhysicsSettings MinDeltaVelocityForHitEvents GetFOVAngle SetGameCameraCutThisFrame StopCameraAnimInst ModifierToRemove CameraCachePrivate CameraLensEffects ClientMessage PlayDynamicForceFeedback ServerSetSpectatorWaiting CustomPlaySpace ReturnReason CursorWidget bIsLocalPlayerController Shift ERendererStencilMask::ERSM_Default ERendererStencilMask::ERSM_64 EHasCustomNavigableGeometry::Yes CanCharacterStepUp GetGenerateOverlapEvents SetAllPhysicsAngularVelocityInDegrees SetCastShadow SetCollisionObjectType SetPhysicsLinearVelocity SetSingleSampleShadowFromStationaryLights NewResponse bMultiBodyOve

OFFSET=0xbd8bad TERM=turn
CONTEXT=punder_0_0_y08 gkdeflect_pk_s01_0_0_y00 gkdeflect_s04_0_0_y02 gkfall_catch_0_0_y10_000 traprun_3_1_s_090_y8_near_breast_act087 kick_long_0_0_y0_stagger_l_000 kick_long_0_0_y0_stagger_l_f045_down gkmovenear_HeisouSlant_4_1 gkmovenear_idlemidturn_045 trap_fastball_0_0_000_y0_sidemid_y0_in_act087 gkprejump_3_3_y05_rotateRun_045 gkrise_faceup_0_0_f090 gkrise_sidewaysnear_l_0_3_f090 gkrise_sidewaysslowknee_l_0_0_000 gkrise_sidewaysslow_l_0_0_090 gksavingCancel_afterback_f00 gkstagger_catch_0_0_y10_000 head_y05_sidle_3_0_000_far head_y06_0_0_090_side head_y09_0_0_090_rear head_y09_sidle_3_0_000_far_rear

OFFSET=0xbd9656 TERM=turn
CONTEXT=p_gk_idle_0_0_idle_guts_05 js_run_3_3_000_push_away autoMove_01_reverse_loop_slant_backslant_3_3_mid autoMove_07_ragged45_front_loop_1_1_mid autoMove_08_ragged45_slant_loop_3_3_STEP_mid coach_0_0_000_normal_position_adjust_high autoMove_30_turn_move_1_1_CIRCLE_mid autoMove_00_bodyangle_00_90_180_00_2_2_near new_dribblerun_2_2_f090_y0_out_tripletouchB_ver02 autoMove_01_reverse_loop_slant_backslant_2_2_STEP_mid_michael catchrun_onehand_3_3_y5 autoMove_04_crank45_loop_2_2_mid_michael autoMove_06_zigzag135_side_loop_1_1_mid_michael autoMove_06_zigzag135_side_loop_2_2_mid_michael autoMove_06_zigzag135_

OFFSET=0xbd9878 TERM=turn
CONTEXT=zigzag135_side_loop_2_2_mid_michael autoMove_06_zigzag135_side_loop_2_2_STEP_mid_michael autoMove_11_bodyangle_rolling_slow_1_1_mid_michael autoMove_11_bodyangle_rolling_slow_2_2_mid_michael head_y07_sidle_short_3_2_f180_act064 autoMove_30_turn_move_3_3_CIRCLE_mid_michael dml_goal_celebrate_0086 gkgoalkick_Quick_long_0_0_000_left Slower_0_3_180 avoidjumpsliding_3_4_000_short_act068_01 avoidjumpsliding_3_4_045_act068_02 avoidslide_1_4_000_rapid_low_push_aside_act068_01 autoMove_02_reverse_stop_rightfront_leftback_2_2_STEP_near_gabriel autoMove_00_dribble_bodyangle_00_90_00_1_1_STEP_near_gabriel nea

OFFSET=0xbda195 TERM=turn
CONTEXT=_1_3_090_at045_act071 enum_dummy339 LongVersion_201123_F027_t01_act068_01 enum_dummy381 enum_dummy422 enum_dummy433 autoMove_05_01_gkmovemid_Sidestep_Angle5_1_1 autoMove_08_02_gkmovemid_Sidestep_Angle5_1_1 autoMove_33_01_gkmovemid_idle_idleturn_0_0 NEARKEEPER_03_01_gkmovenear_0_3_0 NEARKEEPER_04_02_gkmovenear_3_3_BODYTURN_SLANT enum_dummy475 enum_dummy487 enum_dummy513 enum_dummy523 enum_dummy532 enum_dummy556 enum_dummy578 enum_dummy608 block_neardelayside_2_0_y02_000_near_act071 defenseMove_01_neardelayback_3_3_parallel_f045_act071 gkrise_sidewaysuplate_l_0_0_f090 REFEREEC angr_brwnit_bite_soft 

OFFSET=0xbdb0d0 TERM=turn
CONTEXT=ine throw_over_0_0_hard_cancel throw_under_0_0_near_hard linesman_3_3 blockfront_0_0_y00_shoot_reaction_frontfar blockfront_2_0_y03_shoot_reaction fall_lowbody_3_0_l fall_upbody_4_0 stagger_lowbody_3_3_tackle_m0_l stagger_upbody_3_3_v2 goalturn_pointing_2_4_right goalturn_guts_high3 goalturn_guts1 demo_droop_hurry_6 demo_appeal_0_1_at045_3 demo_appeal_hurry_8 demo_cheer_at000_1 TimeUp_0_0_Grad_0_0 TimeUp_1_1_Grad_0_2 TimeUp_1_1_Grad_0_3 TimeUp_3_0_Droop_2_1 dodge_human_stop_3 dodge_ball_0_0_slide_front_low doubletouch_sole_0_3_l headfar_3_0_y9_jostle_f kick_long_3_0_infront_y0_high kickfeint_0_3_y

OFFSET=0xbdb0ec TERM=turn
CONTEXT=el throw_under_0_0_near_hard linesman_3_3 blockfront_0_0_y00_shoot_reaction_frontfar blockfront_2_0_y03_shoot_reaction fall_lowbody_3_0_l fall_upbody_4_0 stagger_lowbody_3_3_tackle_m0_l stagger_upbody_3_3_v2 goalturn_pointing_2_4_right goalturn_guts_high3 goalturn_guts1 demo_droop_hurry_6 demo_appeal_0_1_at045_3 demo_appeal_hurry_8 demo_cheer_at000_1 TimeUp_0_0_Grad_0_0 TimeUp_1_1_Grad_0_2 TimeUp_1_1_Grad_0_3 TimeUp_3_0_Droop_2_1 dodge_human_stop_3 dodge_ball_0_0_slide_front_low doubletouch_sole_0_3_l headfar_3_0_y9_jostle_f kick_long_3_0_infront_y0_high kickfeint_0_3_y0_l fk_long_3_0_inside_syuns

OFFSET=0xbdb100 TERM=turn
CONTEXT=ear_hard linesman_3_3 blockfront_0_0_y00_shoot_reaction_frontfar blockfront_2_0_y03_shoot_reaction fall_lowbody_3_0_l fall_upbody_4_0 stagger_lowbody_3_3_tackle_m0_l stagger_upbody_3_3_v2 goalturn_pointing_2_4_right goalturn_guts_high3 goalturn_guts1 demo_droop_hurry_6 demo_appeal_0_1_at045_3 demo_appeal_hurry_8 demo_cheer_at000_1 TimeUp_0_0_Grad_0_0 TimeUp_1_1_Grad_0_2 TimeUp_1_1_Grad_0_3 TimeUp_3_0_Droop_2_1 dodge_human_stop_3 dodge_ball_0_0_slide_front_low doubletouch_sole_0_3_l headfar_3_0_y9_jostle_f kick_long_3_0_infront_y0_high kickfeint_0_3_y0_l fk_long_3_0_inside_syunsuke fk_long_3_0_insi

OFFSET=0xbdcb22 TERM=turn
CONTEXT=_MEAN receipt_check_retry_count CmdVerifyUserCanBuy CmdSaveReceipt getIconUrl getPriceAmountMicros getRecurrenceMode getItemProductDetails com/android/billingclient/api/Purchase need_refund_detect_notice CmdSaveReceipt.php CmdAuthSteam.php turn_account_param turn_account UgmPrivilegeCheckTask ETF enable_indicator_stats_for_event_id multi_stats_data ue4.http.proxy.proxyPort grpc.minimal_stack grpc.http2.true_binary grpc.channel_id serializer_(*orig_send_message_).ok() assertion failed: %s false && "It is illegal to call GetSendInitialMetadata on a " "method which has a Cancel notification" combiner

OFFSET=0xbdcb35 TERM=turn
CONTEXT=_retry_count CmdVerifyUserCanBuy CmdSaveReceipt getIconUrl getPriceAmountMicros getRecurrenceMode getItemProductDetails com/android/billingclient/api/Purchase need_refund_detect_notice CmdSaveReceipt.php CmdAuthSteam.php turn_account_param turn_account UgmPrivilegeCheckTask ETF enable_indicator_stats_for_event_id multi_stats_data ue4.http.proxy.proxyPort grpc.minimal_stack grpc.http2.true_binary grpc.channel_id serializer_(*orig_send_message_).ok() assertion failed: %s false && "It is illegal to call GetSendInitialMetadata on a " "method which has a Cancel notification" combiner_data_.active_combi

OFFSET=0xbde79c TERM=turn
CONTEXT=ion_id_context ssl_start_async_job tls_construct_cke_ecdhe tls_construct_ctos_sct tls_construct_server_hello tls_parse_ctos_ec_pt_formats tls_parse_stoc_sct bad packet ca dn length mismatch dh public value length is wrong no certificates returned no client cert method ocsp callback failure path too long sslv3 alert unsupported certificate tlsv1 alert unknown ca tls invalid ecpointformat list unknown certificate type RequestCAPath AntiReplay Match/Setup/MatchSetup Match/End/MatchDiscontinueRematch Online/UserCompe/ProcUserCompeLobbyEntrance Settings/SaveDataDelete/SaveDataDelSel is_first_match_no_m

OFFSET=0xbdfc54 TERM=turn
CONTEXT=valid typedef - Missing metadata for: %s, please check the source metadata. mUserAllocated ShadowCapsuleGeometry convexMesh G:\RenderPlat\Engine\Source\ThirdParty\PhysX3\PhysX_3.4\Source\GeomUtils\src\hf\GuHeightField.cpp User allocator returned NULL. PvdMemClient const char* mShaderData PxVehicleConstraintShader mWheelsSimData mSuspensions mDataPairs eId2_%u eTWENTYNINTH MMaxCompression SceneQueryFilterData GearChange PST8PDT VLAT IRKT ADT PMST Chile/EasterIsland ucol_close ibm-942_P120-1999 cesu8 lmbcs16 UTF-7,version=1 gb18030 keis ibm-916_P100-1995 res_index ucol_swap(): data format %02x.%02x

OFFSET=0xbe139f TERM=turn
CONTEXT=riFsWriter_Create has been called before the library initialization. E2009012924 E2008100702 E2008100703 E2008110401 E2011121302:crifsdecomplayla_Create failed to create. E2015040707:[CRI Vip] The work_size should be greater than a value returned criVip_CalcWorkSize2() function. W2021072802:Invalid ID3v2 tag. [ERROR] criVsd_M2tsSplitCreate called twice. [IDR Seek] Delete before IDR: PTS: %lu , offset: %d, consume: %d, First IDR: %s [vodstm] The downloaded playlist unexpectedly became a master playlist. W202107192:[CriAesSegmentsDecryptor] request_headers is NULL but request_num_headers is larger

OFFSET=0xbe5781 TERM=turn
CONTEXT=SettingsSelect::MENU_GAME_SETTINGS_SELECT_CONTROLLER EMenuInputFilterType EMenuLeagueBorderKind::PROMOTION EMenuLeagueBorderKind EDivideCoopTeamStep::DIVIDE_COOP_TEAM_STEP_LOADING GetStrHomeAway ELobbyMainSelectInitState::Start IsInitExitReturn lobbyKind ELobbyRoomReqest::OnChangedAcceptOpenUserList ELobbyRoomReqest::FadeUserList ELayoutMatchMainMenuCoopUserRequest::Home HomeStr DefaultStr DispDefaultAvatar MessagePtr ELayoutStrikeArenaCoopUserInfo ELobbySideSelectSideAnime EMenuMailboxCommandResult::COMMAND_RESULT_ERROR UpdateMain m_footRight0Left1 UpdateLineupData EPauseCameraType::PAUSE_CAMERA_

OFFSET=0xbebfa7 TERM=turn
CONTEXT=t095 stagger_lowbody_3_3_000_v2 gkmovenear_slantstep_0_3_1_short head_y06_sidle_3_2_f090_nojump_v2 head_y06_sidle_chest_3_0_f090_shed dm_oop_ballcome_handup_one_far_f045_idle_0_1_walkbackslant dm_oop_pass_point_000_walk_1_3_run_000 dash_04_turn_4_4_090_CIRCLE_Ortega autoMove_00_bodyangle_00_90_180_00_1_1_STEP_mid_michael autoMove_01_reverse_loop_front_back_2_2_STEP_mid_michael autoMove_05_zigzag135_front_loop_2_2_STEP_mid_michael dml_goal_celebrate_0335 head_y09_jostle_s_0_0_090_act064 avoidjumpsliding_3_3_f045_act079_01 avoidslide_1_4_090_push_aside_act068_02 autoMove_00_dribble_bodyangle_00_180_

OFFSET=0xbecf62 TERM=turn
CONTEXT=ve' chunk hex-length longer than %d http_chunk, added last, empty chunk Excess found writing body: excess = %zu, size = %ld, maxdownload = %ld, bytecount = %ld operation aborted by callback Excessive username length for proxy auth Server returned nothing (no headers, no data) Failed to shut down the SSL connection anonymous %25 SSL certificate verify result: %s (%ld) unable to set private key file: '%s' type %s SSL_ERROR_WANT_CONNECT SSL_ERROR unknown WSS enduranceTorque paramInt ParameterMaskElement Enable_BannerNationalSymbol FIELD DevelopData/common/match/constant/ballPerson/ball_person_st033.j

OFFSET=0xbed6fd TERM=turn
CONTEXT=E_IN en_US es-MX CommandListener BallListener afcon_high j1 camera_person_move_front_0_2 camera_person_move_back_0_2 demo_fail_run_2 dm_miss_run_3_1_walk_angry_high_1 demo_goal_fall_down goalkick_instruction_2_l puntkick_front_0_0 linesman_turn_2_2 seamless_ck_ball_set_3_0_l blockfront_0_0_y02_shoot_reaction fall_lowbody_2_0_v2_l gkstagger_catch_0_0 demo_move_1_1_045 kickfeint_crujiff_4_3_l demo_glad_0_1_000 demo_glad_3_0_000 demo_angry_0_1_135_1 demo_angry_1_1_back demo_gk_angry_10 demo_gk_angry_11 demo_gk_angry_lie_6 demo_angry_hurry_6 demo_angry_hurry_12 demo_miss_0_0_sithip demo_miss_facedown_

OFFSET=0xbf226d TERM=turn
CONTEXT=ck:Construct index[%d][%s] ASSET_PACK_NETWORK_ERROR [%s] cpk_dat/common/etc/appearance/BootsList.bin CompetitionTournamentPositionFor3Rd.bin CoachTactics.bin CoachBooster.bin ClassNotFoundException: %s terminate_handler unexpectedly returned il nx static_cast sizeof b0E b1E li __float128 void __cxxabiv1::scan_eh_tab(scan_results &, _Unwind_Action, bool, _Unwind_Exception *, _Unwind_Context *) : out of range asterisk hyphen percent-sign right-parenthesis G:\RenderPlat\Engine\Source\ThirdParty\PhysX3\PxShared\src\foundation\include/PsHashInternals.h static const char *physx::shdfnd::Reflection

OFFSET=0xbf80e0 TERM=turn
CONTEXT=edAlertRatingChanged SetMenuTrackrecordOpEventTourMainMenu SetupJumpBtnToolTipTwoSettings SetSelectedAgeCategory EEventSettingsControlStyleFilterKind GetCurrentTeamName GetMatchCountAll GetImageTexture category m_isInitialTeamNational CanReturn GetFormation GetTeamMenuFlowEventStr IsDataSyncUpdate NeedDispToolTipMultiFormation SetFlowEvent SwapOrderPlayer exOrderNo1 EGamePlanCustomPlayerSuspensionType::PLAYER_SUSPENTION_NUM EGamePlanCustomPlayerMenuItemType::PLAYER_TRAINING_POSITION EGamePlanCustomMainMenuItemType::OPP_TEAM_INFO EGamePlanCustomDispType::OFFENSIVE_PLAYSTYLE GamePlanMatchAutoSetting

OFFSET=0xbf9ed9 TERM=turn
CONTEXT=etVarArgs() [%s] . Preserve ObjectProperty LazyObjectProperty TextureOffsetParameter Paths ExistingQueuedPackagesQueueDepth AROToken EndOfPointerToken execFinalFunction execNameConst COND_SimulatedOnly COND_SimulatedOrPhysicsNoReplay EAppReturnType::Type EUnit::KilogramsForce EMouseCursor::Hand PF_DXT5 PF_R32_FLOAT PF_G16R16F PF_A8 PF_ATC_RGB PF_ASTC_10x10 InterpCurvePointVector Box2D U F9 LeftAlt Gamepad_RightTriggerAxis Gamepad_Special_Left Gamepad_RightStick_Up RotationRate Steam_Touch_0 Android_Volume_Up Vive_Left_Trigger_Axis Vive_Left_Trackpad_X ValveIndex_Right_Trackpad_Up 3 ValveIndex setD

OFFSET=0xbfef8f TERM=turn
CONTEXT=mid kick_mid_3_0_inside_y0_000_punch head_y07_short_0_0_000_act064 gkunderthrow_3_0_fast dm_oop_gk_side_3_0_seeOff js_idle_0_0_180_guard_back_stagger_hard_main js_idle_0_0_180_guard_back_stagger_main dm_oop_gk_lie_0_1_walkguts_02 dm_oop_gk_turn_135_0_1_walkAngry_02 autoMove_03_crank90_loop_3_3_mid autoMove_04_crank45_loop_3_3_STEP_mid autoMove_06_zigzag135_side_loop_1_1_STEP_mid autoMove_32_go_to_3_3_mid autoMove_07_ragged45_front_loop_2_2_STEP_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_face_only_mid_michael coach_0_1_f090_hands_waist_oop_protest coach_1_1_090_cross_arms_oop_g

OFFSET=0xbff091 TERM=turn
CONTEXT=ngry_02 autoMove_03_crank90_loop_3_3_mid autoMove_04_crank45_loop_3_3_STEP_mid autoMove_06_zigzag135_side_loop_1_1_STEP_mid autoMove_32_go_to_3_3_mid autoMove_07_ragged45_front_loop_2_2_STEP_mid_michael autoMove_10_bodyangle_keep_circle_bigturn_front_2_2_face_only_mid_michael coach_0_1_f090_hands_waist_oop_protest coach_1_1_090_cross_arms_oop_glad autoMove_32_go_to_3_3_mid_michael Slower_0_3_135 avoidjumpsliding_4_4_f022_act079_01 autoMove_03_crank90_loop_3_3_near_gabriel autoMove_00_bodyangle_00_180_00_2_2_STEP_near_gabriel autoMove_01_dribble_reverse_loop_front_back_3_3_STEP_near_gabriel ballTou

OFFSET=0xbffa18 TERM=turn
CONTEXT=1_run new_walk_1_3_run enum_dummy110 enum_dummy111 new_dribbleslide045_3_0_000_in_Ltouch_ver12 enum_dummy154 enum_dummy198 LongVersion_200127_F012_t01_Gabriel enum_dummy217 enum_dummy252 enum_dummy290 autoMove_40_circle_short_neardelayside_turn_3_3_bodyangle_keep_act079 dash_06_backslant_2_4_parallel_045_act071 dash_06_side_2_4_run_f270_act080 dash_06_slant_2_4_run_f180_act068 pull_ball_foot_2_0_000 pull_ball_foot_3_0_180 dm_oop_gk_jog_2_0_Glad_180_v02 dm_oop_gk_riseup_0_0_sideways_mortifying_000_v02 dm_oop_angry_1_3_180_act071_02 dm_oop_praise_1_3_180_at090_act064_01 enum_dummy312 enum_dummy320 e

OFFSET=0xc011f5 TERM=turn
CONTEXT=_thigh_mid trapside_l_3_0_y6_instep_far trapside_l_3_0_y8_in_far trapside_r_3_3_y2_instep_subhit trapside_r_4_4_y3_thigh trapthroughrun_3_4_y5 trapthrough_3_0_y0 gkrise_sidewaysAction1_l demo_appeal_2_1_135_2 tackle_3_0_near_parallel springturn_3_3_r holdEnd=%d animeFrame=%d *************EVENT_TO_LAYER_ONE cpk_dat/common/anime/AnimeTable/bin/Animetable.bin [Command] ControlMode [%s](enemy pass touch but highball and touch enable playpoint) [Command] ControlMode [%s](team ai is offence & other player keep or follow) [Command] ControlMode [%s] (even kick off) TvHandyCameraMan.R_BackCam ====

OFFSET=0xc04b5b TERM=turn
CONTEXT=ne/EvCompe/EventCompe/ProcEvCompeRootInit Online/EvCompe/MlEvent/Match/ProcMlEventPreSkipMatchFromGamePlan Online/Season/ProcSeasonRestart Online/Setting/OnlineLanguage Online/UserCompe/ProcUserCompePreMain match_direct gk_uniform_number return_record LobbyRoomCheckGoMatchForceProceed OnlineMatchInit injuryLength USERT BGM1_LIC_CMP%04d_CHAMP cpk_snd/%s/sound/config/Rc/ RC_ROOT RC_04D SU_10_B SA_C_NMB_E22 SA_C_NMB_E65 SA_C_NMB_E83 SA_C_NMB_E96 SA_C_NMB10 SA_C_NMB36 SA_C_NMB40 SA_C_NMB87 se_config.bin Error reading Element value. RE A1_T6 GT CheckDemoVariousData SetTempFlagForConfigMessageBoard SetT

OFFSET=0xc09e63 TERM=turn
CONTEXT=Game/Assets/ui/widget/facility/uiBgChanger/uiBgLinkTable_ML.uiBgLinkTable_ML Image_42 ar STextBlockWithRuby GetSkinTexturePath NormalEditableText UUiTextBase::SetForceIgnoreCreatingTextureDefault call. device : %s, hardware:%s AddWindow return %s [Footer] Request Update Footer %s [Footer] FadeOut Footer %s win:%s ---------UVipPlayerController::OnSegmentChangeFunc ------------ EAudiAreaTeam UsingStandArea TeamFloorInstanceRatios PauseAutoPilot zorder ChangedDemoBool GetTeamEmblemForCoverSub NewClothBlendWeight shortPosH m_face m_captain_band_compo GetInactiveAnimation PlayDecideReleasedAni

OFFSET=0xc0aa3d TERM=turn
CONTEXT=AMSTYLE EDetailViewParamExplainType::PARAM_EXPLAIN_TYPE_PLAYER_SINGLE_COM_PLAYSTYLE CallbackClass isEntered m_isEntered m_isTeamSelect m_textColorA_b eventProgress m_fStrEventType m_isGameLevelChangeable m_fStrTeam SetupMedalBorderTime OnReturn EFriendListChoiceApplicationType::FriendListChoiceApplicationTypeUser CallBackView CloseChangeFormationViewCallbackEvent__DelegateSignature selectIndex CallBackEventCloseView GetBtnWidget SetAlertCloseSE EMenuMenuIconAlertOneBtnIconKind::Icon_Talent Title m_itemListOther m_pTaskMlEventSmartphoneManager SwitchTextColorInStep3Home ACTIONVIEW_ITEM_TYPE::ACTION

OFFSET=0xc1258b TERM=turn
CONTEXT=_ver21 traprun_guardback_1_1_090_y0_sole_ver03 stagger_upbody_3_3_090_weakly_v3 js_run_2_3_000_push_away autoMove_06_zigzag135_side_loop_3_3_mid autoMove_07_ragged45_front_loop_2_2_mid coach_0_1_090_hands_waist_oop_protest_high autoMove_30_turn_move_2_2_CRANK_mid coach_0_1_090_normal_oop_glad autoMove_00_bodyangle_00_90_f90_00_2_2_STEP_near autoMove_01_reverse_loop_slant_turn_3_3_mid_michael autoMove_07_dribble_ragged45_front_loop_3_3_mid_gabriel autoMove_11_bodyangle_rolling_fast_2_2_mid_michael autoMove_11_dribble_bodyangle_rolling_slow_3_3_mid_gabriel coach_1_1_f090_cross_arms_oop_protest_high 

OFFSET=0xc12611 TERM=turn
CONTEXT=op_3_3_mid autoMove_07_ragged45_front_loop_2_2_mid coach_0_1_090_hands_waist_oop_protest_high autoMove_30_turn_move_2_2_CRANK_mid coach_0_1_090_normal_oop_glad autoMove_00_bodyangle_00_90_f90_00_2_2_STEP_near autoMove_01_reverse_loop_slant_turn_3_3_mid_michael autoMove_07_dribble_ragged45_front_loop_3_3_mid_gabriel autoMove_11_bodyangle_rolling_fast_2_2_mid_michael autoMove_11_dribble_bodyangle_rolling_slow_3_3_mid_gabriel coach_1_1_f090_cross_arms_oop_protest_high coach_1_1_f090_cross_arms_position_down dml_goal_celebrate_0348 dml_goal_celebrate_0349 feintrun_bodyfake_front_3_3_000_y0_ver20 autoM

OFFSET=0xc12eeb TERM=turn
CONTEXT=relax new_walkback_1_1_walk_f090_warning new_walk_1_1_walkback_045_relax new_walk_1_2_run_045_relax new_dribble_0_3_000_side_y0_in_ver21 LongVersion_171104_F114_t02_Gabriel_01 enum_dummy190 enum_dummy225 enum_dummy245 enum_dummy259 dash_04_turn_4_4_135_act079 dash_06_backslant_2_4_run_f090_act071 dash_06_back_2_4_parallel_act068 dash_06_side_2_4_parallel_090_act080 dash_06_side_2_4_parallel_f225_act080 dash_07_dash_4_2_runslant_near_ball_follow_act071 dm_oop_gk_jog_2_0_mortifying_180 dm_oop_droop_3_3_090_act071 dm_oop_praise_3_3_000_at045_act064 enum_dummy338 LongVersion_201123_F028_t01_act068_02 

OFFSET=0xc13ee6 TERM=turn
CONTEXT=%d , + Burst : %.2f(m) camera_person_move_side_2_0 demo_move_0_1_2 demo_move_1_1_1 dm_oop_allfours_0_1_walk_miss goalkick_coaching_up_l throw_over_0_0 throw_over_3_0_cancel judge_advantage_3 linesman_throughin_right_hand linesman_run_2_2_turn seamless_carry_ball_move_0_2 blockfront_2_0_y03_shoot_reaction_v3 blockside_2_0_y02 fall_lowbody_0_0_v2_l fall_lowbody_2_0_v2_r stagger_upbody_3_3_hard_v3 demo_move_3_1_135_2 demo_move_3_1_135_face demo_move_3_1_135_sweat demo_move_4_1_lineout_135 demo_gk_glad_lie_1 demo_angry_0_1_135_3 demo_appeal_notouch_045 demo_praise_hurry_6 demo_praise_hurry_13 demo_p

OFFSET=0xc15d10 TERM=turn
CONTEXT=_TIME P2PTURNIO_RTT_MEAN_EVALUATION PING_ANTENNA_LEVEL END_REASON OPERATION_TYPE CS_SERVER_NAME GAME_SERVER_STATS_URL TRANSPORT_RTT_MAX CmdConsumeItem consumeItem nativeOnGetBillingConfigFinished pes_receipt CmdSendNotice.php wait_msec_cmd_turn_address on_sys_common_thread_pool fri statvfs error grpc.max_connection_age_ms grpc.enable_channelz G:/PES22HC/Dev-600Series/Source/Shared/basic/ext/grpc/grpc/include/grpcpp/impl/codegen/grpc_library.h callback_ Couldn't initialize byte buffer reader count <= static_cast<int>(GRPC_SLICE_LENGTH(*slice_)) false && "It is illegal to call ModifySendMessage on a

OFFSET=0xc1682c TERM=turn
CONTEXT=s\Source\Shared\basic\ext\grpc\grpc\src\core\ext\filters\client_channel\resolver\dns\native\dns_resolver.cc field:maxRequestMessageBytes error:should be of type number message_size CHECK failed: (buffer_size) >= (0): CHECK failed: (last_returned_size_) > (0): G:\PES22HC\Dev-600Series\Source\Shared\basic\ext\grpc\grpc\third_party\protobuf\src\google\protobuf\io\zero_copy_stream.cc "). Note that the exact same class is required; not just the same descriptor. subtype mismatch proto3 Messages can't have default values! ", which is not defined. The innermost scope is searched first in name resolutio

OFFSET=0xc19fe7 TERM=turn
CONTEXT=rround Effect is usable only at 48 kHz output. E2009071603:Insufficient buffer size. E2011051331 E2020021821:criFs_SetFileAccessThreadStackSize must call before initialization. CrcMode E2008071630 E2011121404:criFsDecodeDevice_GetDecoder return NULL. E2008070933:Can not allocate group loader handle. (Increase num_group_loaders of CriFsConfig.) E2008091156 E2012062200 E2008090350 W2018102997:Failed to write '%s'. #CRIFS,%u,%d,OpenEnd,%s,%lld,%lld,%s,%lld,%d E2012070602 E2019030101:[CRI Vip] The work_size must be 0 or greater than 0. E2019030103:[CRI Vip] The work_ptr should be not null if the wor

OFFSET=0xc1a27b TERM=turn
CONTEXT=am path is empty. Please set a stream path by criVip_SetStreamPath(). W2021072801:Invalid ID3v2 tag. #EXT-X-DISCONTINUITY [ERROR] criVsd_M2tsSplitCreate() failed. Could not create demux thread. [CRIVSD] Failed in criVsd_VideoFrameReset() return 0x%08x sar-width [vodstm] The current HLS playlist is updated with discontinuous segments during live streaming. E2018122605:CriAesDecryptorAndroid failed to create JVM local frame. [CriAesSegmentsDecryptor] Invalid segment size (%lu). Should be 16*n byte. MPEGTS: " ~J - y e ~ A x \ H \ $ & 

OFFSET=0xc93f3f TERM=turn
CONTEXT= !'- ) 2 b3M ( 7;? u ' 1 K y 6 + @ < i "+ 8 $ $ .] Z ; S health checking Watch method returned UNIMPLEMENTED; disabling health checks but assuming server is healthy #' # ' s l ~ 7 ~ T s * _ J [[ ?]b ,8 @% _i grpclb_client_stats

OFFSET=0xcccb2f TERM=turn
CONTEXT=647UObjectE N6icu_647UMemoryE ' ToCP $$$$$$$$$$$$$$ = = = = = = = = = = = = = = = = = T = = = = = = y = = $ = = E / * 4 NReturns. Returns %d. Returns. Status = %d. Returns %d. Status = %d. Returns %d. Status = %p. = ? ? ? ? = ? ? iiiiiiiiiiiiiiiii,iiiiiiiiiii7iiBJ BBB BBBBBBBBO cnv 

OFFSET=0xcccb38 TERM=turn
CONTEXT=tE N6icu_647UMemoryE ' ToCP $$$$$$$$$$$$$$ = = = = = = = = = = = = = = = = = T = = = = = = y = = $ = = E / * 4 NReturns. Returns %d. Returns. Status = %d. Returns %d. Status = %d. Returns %d. Status = %p. = ? ? ? ? = ? ? iiiiiiiiiiiiiiiii,iiiiiiiiiii7iiBJ BBB BBBBBBBBO cnv abcde

OFFSET=0xcccb44 TERM=turn
CONTEXT=UMemoryE ' ToCP $$$$$$$$$$$$$$ = = = = = = = = = = = = = = = = = T = = = = = = y = = $ = = E / * 4 NReturns. Returns %d. Returns. Status = %d. Returns %d. Status = %d. Returns %d. Status = %p. = ? ? ? ? = ? ? iiiiiiiiiiiiiiiii,iiiiiiiiiii7iiBJ BBB BBBBBBBBO cnv abcdefghijklmnopq

OFFSET=0xcccb5b TERM=turn
CONTEXT= ' ToCP $$$$$$$$$$$$$$ = = = = = = = = = = = = = = = = = T = = = = = = y = = $ = = E / * 4 NReturns. Returns %d. Returns. Status = %d. Returns %d. Status = %d. Returns %d. Status = %p. = ? ? ? ? = ? ? iiiiiiiiiiiiiiiii,iiiiiiiiiii7iiBJ BBB BBBBBBBBO cnv abcdefghijklmnopqrstuvwxyz abcdefgh

OFFSET=0xcccb75 TERM=turn
CONTEXT=oCP $$$$$$$$$$$$$$ = = = = = = = = = = = = = = = = = T = = = = = = y = = $ = = E / * 4 NReturns. Returns %d. Returns. Status = %d. Returns %d. Status = %d. Returns %d. Status = %p. = ? ? ? ? = ? ? iiiiiiiiiiiiiiiii,iiiiiiiiiii7iiBJ BBB BBBBBBBBO cnv abcdefghijklmnopqrstuvwxyz abcdefghijklmnopqrstuvwxyz 

OFFSET=0xcfb0d6 TERM=turn
CONTEXT=tevg fCi nefeedCa@bpc Ue g l8 ue9 i#l4m biguous#$ phabetic% 2'a)b+k-r eak a6b>s ymbolsW fter) e*o th' fore+ mQm3o(pir5 mvn d<t ingentbreak/ itiona ljapanesestarterk b:p lexcontextQ iningmark3ajb/jkl0 osep a8u nctuation1 renthesisi rriagereturn5 b>mFx6 clamation7p aseqr odifiers dBn o2u& meric' ne! e.i$ git%" cimal# n t aw w Lx py zz s s4xByHz zz g y e m xx f yy!a0iXm th n a&b bazarsquare nh# a0cZo le n<r a ngciti cho ho p,s ux e eo ir iistJu v a,i sp d i c i c g6ghhli b:fJr h uta e$to tano inagh lgu a a$imj naka0e [f ng l!l2m8nDv t e u i$lg lg g ut g6iRk r i 

OFFSET=0xcfffc8 TERM=turn
CONTEXT=oining R Right_Joining T Transparent lb Line_Break XX Unknown AI Ambiguous AL Alphabetic B2 Break_Both BA Break_After BB Break_Before BK Mandatory_Break CB Contingent_Break CL Close_Punctuation CM Combining_Mark CR Carriage_Return EX Exclamation GL Glue HY Hyphen ID Ideographic IN Inseparable Inseperable IS Infix_Numeric LF Line_Feed NS Nonstarter NU Numeric OP Open_Punctuation PO Postfix_Numeric PR Prefix_Numeric QU Quotation SA Complex_Context SG Surrogate SP Space SY Break_Symbols ZW ZWSpace NL Next_Line WJ Word_Joiner H2 H2 H3 H3 JL JL JT JT JV JV CP Clo

OFFSET=0xd20476 TERM=turn
CONTEXT= !"# !"# .null nonmarkingreturn notequal infinity lessequal greaterequal partialdiff summation product pi integral Omega radical approxequal Delta nonbreakingspace lozenge apple franc Gbreve gbreve Idotaccent Scedilla scedilla Cacute cacute Ccaron ccaron dcroat .notdef space exclam quotedbl numbersign dollar percent ampersand quoteright parenleft parenright asterisk plus comma hyphen peri

OFFSET=0xd3100c TERM=turn
CONTEXT="""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""" " """"""""""" """"""d " ?)H&&&& QQQQQQQ QQQQQQQW]LLLL QQQQQQQ QQW"QQQQQlr.notdef .null nonmarkingreturn space exclam quotedbl numbersign dollar percent ampersand quotesingle parenleft parenright asterisk plus comma hyphen period slash zero one two three four five six seven eight nine colon semicolon less equal greater question at A B C D E F G H I J K L M N O P Q R S T U V W X Y Z bracketleft backslash bracketright asciicircum underscore grave a b c d e f g h

OFFSET=0xa3a716 TERM=DTLS
CONTEXT=ty bad write retry compression library error dane tlsa bad digest length ecc cert not for signing library bug missing sigalgs extension read timeout expired sslv3 alert certificate expired tlsv1 unsupported extension wrong certificate type DTLSv1.2 ChainCAPath SSLv3/TLS read next proto SSL negotiation finished successfully SSLv3/TLS write server done TRCCS certificate unobtainable CLIENT_RANDOM rsa_pkcs1_md5_sha1 Intro/ProcessIntroUserCheck Exhibition/ProcessExhibiMatchInit Match/MatchReplay Match/Setup/MatchSetupRematch Match/PathToGlory/PathToGloryHintDialogEnd Match/Sugoroku/SugorokuLoopRewardE

OFFSET=0xa4d7ec TERM=DTLS
CONTEXT=ion type invalid srp username missing fatal no ciphers specified psk no client cb signature algorithms error tlsv1 alert decryption failed tls illegal exporter label unable to find ecdh parameters Require SSLv3/TLS write change cipher spec DTLS1 read hello verify request TLSv1.3 pending early data end certificate expired ed448 Match/Setup/MatchSetupNoDemo Tutorial/TutorialIntroStepupEnd Online/Lobby/StrikeArena/ProcLobbyStrikeArenaPreAssetPreview Online/EvCompe/PresetCoop/ProcEvCompeEventEnter Online/EvCompe/Tournament/ProcEvCompeOutFromGroupMatchRoot sugoroku_clear get_go_around_present_list expT

OFFSET=0xa60d12 TERM=DTLS
CONTEXT=te B mode compression disabled compression id not within private range empty srtp protection profile list inconsistent compression invalid key update type tlsv1 alert inappropriate fallback tlsv1 alert insufficient security unknown command DTLSv1 no_tls1_1 no_tls1_2 ecdh_single chainCApath TLSv1.3 write server certificate verify TWCCS TRCC MatchMenuSub/MatchMenuEnd Match/Setup/MatchOnlineSetup Match/Setup/MatchDirectTrainingSetup Match/Gimmick/GimmickMatchStartWindowEnd MyClub/Contract/ProcessGotPlayerDetailBanner Common/ContentList/ProcessContentList Online/Match/MatchProcessMatchSettingsEnd Onli

OFFSET=0xa99f59 TERM=DTLS
CONTEXT=tch request sent ssl session id callback failed tlsv13 alert certificate required unexpected record unknown cipher returned wrong ssl version wrong version number Ciphersuites ECDHSingle Peer RequestPostHandshake SSLv3/TLS read server done DTLS1 write hello verify request TWSKE Intro/IntroEnd Match/Pause/MatchPauseWaitView Match/Setup/MatchFTUESetup Tutorial/TutorialPlayEnd Match/PathToGlory/PathToGloryFailureDialogEnd GamePlan/ProcessGamePlanInherit Online/Match/MatchProcessPreMenu Online/Lobby/StrikeArena/ProcLobbyStrikeArenaPreUniformPreview Online/EvCompe/Tour/ProcEvCompeEventEnter Online/EvCo

OFFSET=0xaad99b TERM=DTLS
CONTEXT=stoc_ems tls_process_cert_status_body tls_process_cke_psk_preamble tls_process_client_certificate wpacket_intern_init_len bad key share bad psk cannot change cipher invalid compression algorithm invalid context unexpected end of early data DTLSv0.9 groups AllowNoDHEKEX SSLv3/TLS write next proto SSLv3/TLS read server hello SSLv3/TLS read finished SSLv3/TLS write session ticket TLSv1.3 read end of early data SSLERR DRCHV DWCHV UNKWN SERVER_HANDSHAKE_TRAFFIC_SECRET Intro/ProcessIntroAgeCheck Online/EvCompe/EventCompe/TeamChange/ProcessPreGamePlan Online/EvCompe/MlEvent/ProcMlEventPreMain Online/EvC

OFFSET=0xb7deec TERM=DTLS
CONTEXT=ES_128_CCM DHE-PSK-AES256-CCM8 ECDHE-ECDSA-AES128-CCM TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384 TLS_RSA_PSK_WITH_AES_256_CBC_SHA384 TLS_ECDHE_PSK_WITH_NULL_SHA256 SRP-AES-128-CBC-SHA RSA-PSK-ARIA256-GCM-SHA384 psk_identity_hint PSK aNULL DHE DTLSv1_listen ossl_statem_server_process_message SSL_CTX_use_PrivateKey SSL_CTX_use_psk_identity_hint SSL_CTX_use_RSAPrivateKey_ASN1 SSL_CTX_use_RSAPrivateKey_file SSL_peek SSL_SESSION_set1_id_context tls1_get_curvelist tls_parse_stoc_key_share tls_process_end_of_early_data tls_setup_handshake cipher or hash unavailable invalid sequence number protocol is shutdo

OFFSET=0xc04711 TERM=DTLS
CONTEXT= TLS_DH_anon_WITH_AES_256_GCM_SHA384 TLS_ECDHE_ECDSA_WITH_NULL_SHA ECDHE-RSA-AES256-SHA384 DHE-PSK-NULL-SHA TLS_RSA_PSK_WITH_NULL_SHA PSK-AES128-CBC-SHA TLS_DHE_PSK_WITH_AES_256_CBC_SHA384 TLS_FALLBACK_SCSV AESCCM8 derive_secret_key_and_iv DTLS_RECORD_LAYER_new dtls_wait_for_dry ssl3_get_record SSL_CTX_use_certificate SSL_enable_ct ssl_generate_session_id SSL_set_alpn_protos tls_construct_cke_rsa tls_parse_ctos_psk_kex_modes tls_prepare_client_certificate tls_process_server_done callback failed cert cb error connection type not set dane tlsa null data decryption failed or bad record mac http reque

OFFSET=0x9c8a8d TERM=dtls
CONTEXT=ASN1 master_key tlsext_tick MEDIUM ssl_cache_cipherlist SSL_client_hello_get1_extensions_present tls13_final_finish_mac tls_construct_cke_gost tls_construct_stoc_cryptopro_bug bad ecc cert binder does not verify dane tlsa bad matching type dtls message too big no verify cookie callback old session cipher not returned sslv3 alert certificate unknown ssl session id has bad length tlsv1 unrecognized name unable to find public key parameters unsupported ssl version legacy_server_connect ciphersuites chainCAfile SSLv3/TLS read change cipher spec PINIT TRCV TED access denied rsa_pss_pss_sha256 rsa_pss_

OFFSET=0x9ef652 TERM=dtls
CONTEXT=S128-CBC-SHA TLS_RSA_PSK_WITH_AES_128_CBC_SHA TLS_PSK_WITH_AES_256_GCM_SHA384 SRP-RSA-AES-256-CBC-SHA TLS_DHE_RSA_WITH_ARIA_256_GCM_SHA384 PSK-ARIA128-GCM-SHA256 tlsext_tick_age_add alpn_selected SSL for verify callback aDSS ciphersuite_cb dtls1_hm_fragment_new OPENSSL_init_ssl SSL_CTX_new SSL_CTX_use_PrivateKey_file SSL_peek_ex SSL_SESSION_print_fp SSL_set_wfd ssl_validate_ct tls13_enc tls_early_post_process_client_hello tls_parse_ctos_sig_algs bad packet length dane tlsa bad certificate usage digest check failed missing rsa signing cert no private key assigned no_ticket serverpref MaxProtocol nu

OFFSET=0xa27ca2 TERM=dtls
CONTEXT=m noticeref policyIdentifier permittedSubtrees language s2i_skey_id error in extension invalid null name TLS_RSA_WITH_AES_128_CBC_SHA DHE-RSA-AES128-GCM-SHA256 TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA384 TLS_SRP_SHA_RSA_WITH_AES_256_CBC_SHA FIPS dtls1_buffer_record dtls1_write_app_data_bytes ssl_read_internal SSL_renegotiate SSL_write tls_choose_sigalg tls_construct_ctos_ems tls_construct_server_certificate tls_process_encrypted_extensions tls_process_hello_retry_request bad hello request cipher code wrong length clienthello tlsext inappropriate fallback can't find SRP server param mixed handshake and n

OFFSET=0xa27cb6 TERM=dtls
CONTEXT=entifier permittedSubtrees language s2i_skey_id error in extension invalid null name TLS_RSA_WITH_AES_128_CBC_SHA DHE-RSA-AES128-GCM-SHA256 TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA384 TLS_SRP_SHA_RSA_WITH_AES_256_CBC_SHA FIPS dtls1_buffer_record dtls1_write_app_data_bytes ssl_read_internal SSL_renegotiate SSL_write tls_choose_sigalg tls_construct_ctos_ems tls_construct_server_certificate tls_process_encrypted_extensions tls_process_hello_retry_request bad hello request cipher code wrong length clienthello tlsext inappropriate fallback can't find SRP server param mixed handshake and non handshake data ov

OFFSET=0xa60b14 TERM=dtls
CONTEXT=_WITH_AES_128_CBC_SHA PSK-NULL-SHA384 TLS_RSA_PSK_WITH_NULL_SHA256 GOST2001-GOST89-GOST89 TLS_RSA_WITH_ARIA_128_GCM_SHA256 TLS_ECDHE_ECDSA_WITH_ARIA_256_GCM_SHA384 TLS_DHE_PSK_WITH_ARIA_256_GCM_SHA384 psk_identity SRP SUITEB192 aGOST12 EDH dtls_construct_change_cipher_spec ssl_cipher_list_to_bytes ssl_set_cert_and_key SSL_write_early_data tls12_check_peer_sigalg tls_construct_extensions tls_construct_stoc_use_srtp tls_parse_ctos_supported_groups use_certificate_chain_file at least (D)TLS 1.2 needed in Suite B mode compression disabled compression id not within private range empty srtp protection p

OFFSET=0xae5fbe TERM=dtls
CONTEXT=_WITH_AES_128_GCM_SHA256 TLS_DHE_PSK_WITH_NULL_SHA TLS_PSK_WITH_NULL_SHA384 DHE-PSK-AES128-CBC-SHA256 TLS_DHE_RSA_WITH_ARIA_128_GCM_SHA256 ECDHE-ARIA256-GCM-SHA384 TLS_EMPTY_RENEGOTIATION_INFO_SCSV peer (NONE) CAMELLIA EDH-RSA-DES-CBC3-SHA dtls1_check_timeout_num ossl_statem_server_read_transition pqueue_new ssl3_setup_key_block SSL_CTX_set_tlsext_max_fragment_length SSL_CTX_use_RSAPrivateKey SSL_set_cipher_list SSL_use_PrivateKey SSL_use_RSAPrivateKey_file tls1_setup_key_block tls_parse_stoc_status_request tls_process_ske_psk_preamble bad srp a length compression failure decryption failed ee key 

OFFSET=0xb0c8b7 TERM=dtls
CONTEXT=id ipaddress AES128-SHA DHE-RSA-AES128-SHA TLS_DHE_RSA_WITH_AES_256_CBC_SHA256 TLS_RSA_WITH_AES_128_GCM_SHA256 TLS_PSK_WITH_AES_256_CCM_8 ECDHE-RSA-AES128-GCM-SHA256 ECDHE-PSK-AES128-CBC-SHA256 construct_key_exchange_tbs d2i_SSL_SESSION do_dtls1_write SSL_CTX_set_session_id_context ssl_session_dup SSL_use_RSAPrivateKey_ASN1 tls1_PRF tls_construct_ctos_ec_pt_formats tls_process_server_hello application data after close notify bad ecpoint bad handshake length custom ext handler already installed no change following hrr sslv3 alert bad certificate tlsv1 alert decrypt error tlsv1 alert export restrict

OFFSET=0xb4582d TERM=dtls
CONTEXT=i_GENERAL_NAME_ex v2i_POLICY_CONSTRAINTS X509V3_EXT_i2d invalid asrange TLS_ECDHE_ECDSA_WITH_AES_256_CCM_8 RSA-PSK-AES256-GCM-SHA384 DHE-PSK-AES256-CBC-SHA384 DHE-PSK-NULL-SHA256 TLS_SRP_SHA_DSS_WITH_AES_256_CBC_SHA 3DES RC2 dane_mtype_set dtls1_read_bytes dtls1_retransmit_message ssl_choose_client_version SSL_key_update ssl_peek_internal SSL_shutdown tls_construct_ctos_npn tls_construct_ctos_renegotiate tls_construct_new_session_ticket tls_process_finished bad cipher dane not enabled sslv3 alert handshake failure cmd= bugs dhparam automatic SSLv3/TLS read certificate status TLSv1.3 read encrypted

OFFSET=0xb4583e TERM=dtls
CONTEXT= v2i_POLICY_CONSTRAINTS X509V3_EXT_i2d invalid asrange TLS_ECDHE_ECDSA_WITH_AES_256_CCM_8 RSA-PSK-AES256-GCM-SHA384 DHE-PSK-AES256-CBC-SHA384 DHE-PSK-NULL-SHA256 TLS_SRP_SHA_DSS_WITH_AES_256_CBC_SHA 3DES RC2 dane_mtype_set dtls1_read_bytes dtls1_retransmit_message ssl_choose_client_version SSL_key_update ssl_peek_internal SSL_shutdown tls_construct_ctos_npn tls_construct_ctos_renegotiate tls_construct_new_session_ticket tls_process_finished bad cipher dane not enabled sslv3 alert handshake failure cmd= bugs dhparam automatic SSLv3/TLS read certificate status TLSv1.3 read encrypted extensions TWCV 

OFFSET=0xb6ae12 TERM=dtls
CONTEXT= creating extension invalid proxy policy setting need organization and numbers TLS_AES_128_CCM_SHA256 RSA-PSK-AES256-CBC-SHA TLS_DHE_PSK_WITH_AES_256_GCM_SHA384 SRP-RSA-AES-128-CBC-SHA session_id_context construct_stateful_ticket ct_strict dtls1_process_record final_maxfragmentlen ossl_statem_server_post_process_message ssl3_read_bytes ssl_cert_set0_chain SSL_read_ex ssl_set_cert tls1_set_groups tls_construct_ctos_session_ticket tls_construct_ctos_srp tls_construct_stoc_cookie tls_construct_stoc_supported_groups tls_parse_ctos_sig_algs_cert tls_process_hello_req bad data cert length mismatch data 

OFFSET=0xba5159 TERM=dtls
CONTEXT=C_SHA AES256-CCM TLS_RSA_WITH_AES_128_CCM_8 TLS_RSA_WITH_AES_256_CCM_8 TLS_RSA_PSK_WITH_AES_128_GCM_SHA256 PSK-AES256-CBC-SHA384 TLS_RSA_PSK_WITH_AES_128_CBC_SHA256 TLS_RSA_WITH_ARIA_256_GCM_SHA384 TLS_DHE_DSS_WITH_ARIA_256_GCM_SHA384 ECDH dtls1_process_buffered_records final_ec_pt_formats ossl_statem_client_read_transition parse_ca_names ssl3_generate_key_block SSL_add_file_cert_subjects_to_stack ssl_bad_method SSL_set_session SSL_use_PrivateKey_file tls_construct_certificate_request tls_parse_ctos_ems tls_parse_ctos_key_share tls_process_certificate_request tls_process_cke_ecdhe tls_process_key_

OFFSET=0xbb85d5 TERM=dtls
CONTEXT=SA-AES256-CCM8 TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA PSK-NULL-SHA256 TLS_SRP_SHA_DSS_WITH_AES_128_CBC_SHA ECDHE-ECDSA-ARIA256-GCM-SHA384 TLS_ECDHE_RSA_WITH_ARIA_256_GCM_SHA384 ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384 aRSA dtls1_read_failed dtls_process_hello_verify ssl3_ctx_ctrl ssl3_do_change_cipher_spec ssl3_init_finished_mac ssl_do_config tls13_restore_handshake_digest_for_pha tls1_set_sigalgs tls_construct_cke_dhe tls_construct_ctos_psk tls_construct_ctos_supported_versions tls_construct_ctos_use_srtp tls_handle_status_request tls_parse_ctos_srp tls_parse_ctos_use_srtp tls_pr

OFFSET=0xbb85e7 TERM=dtls
CONTEXT=_ECDHE_ECDSA_WITH_AES_256_CBC_SHA PSK-NULL-SHA256 TLS_SRP_SHA_DSS_WITH_AES_128_CBC_SHA ECDHE-ECDSA-ARIA256-GCM-SHA384 TLS_ECDHE_RSA_WITH_ARIA_256_GCM_SHA384 ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384 aRSA dtls1_read_failed dtls_process_hello_verify ssl3_ctx_ctrl ssl3_do_change_cipher_spec ssl3_init_finished_mac ssl_do_config tls13_restore_handshake_digest_for_pha tls1_set_sigalgs tls_construct_cke_dhe tls_construct_ctos_psk tls_construct_ctos_supported_versions tls_construct_ctos_use_srtp tls_handle_status_request tls_parse_ctos_srp tls_parse_ctos_use_srtp tls_process_initial_serv

OFFSET=0xbde5ea TERM=dtls
CONTEXT=y Mapping -0x level_add_node invalid numbers DHE-DSS-AES128-SHA256 ECDHE-ECDSA-AES256-GCM-SHA384 DHE-PSK-AES256-GCM-SHA384 TLS_DHE_PSK_WITH_NULL_SHA384 TLS_ECDHE_PSK_WITH_AES_256_CBC_SHA tlsext_hostname kDHE GOST89MAC create_ticket_prequel dtls_get_reassembled_message ossl_statem_client_write_transition ssl3_setup_read_buffer ssl_check_srp_ext_ClientHello SSL_CIPHER_description SSL_clear SSL_CTX_set_client_cert_engine SSL_set_session_id_context ssl_start_async_job tls_construct_cke_ecdhe tls_construct_ctos_sct tls_construct_server_hello tls_parse_ctos_ec_pt_formats tls_parse_stoc_sct bad packet ca

OFFSET=0xbf1719 TERM=dtls
CONTEXT=28-SHA TLS_ECDH_anon_WITH_NULL_SHA ECDHE-RSA-AES128-SHA256 TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256 RSA-PSK-AES128-GCM-SHA256 TLS_SRP_SHA_RSA_WITH_AES_128_CBC_SHA TLS_PSK_WITH_ARIA_128_GCM_SHA256 ECDHE construct_stateless_ticket do_ssl3_write dtls1_write_bytes ssl3_digest_cached_records ssl3_output_cert_chain ssl3_setup_write_buffer tls1_export_keying_material tls_construct_stoc_psk tls_parse_ctos_renegotiate tls_parse_ctos_session_ticket tls_process_cert_verify compressed length too long illegal point compression inconsistent early data sni invalid ticket keys length library has no ciphers no cipher

OFFSET=0xc04727 TERM=dtls
CONTEXT=256_GCM_SHA384 TLS_ECDHE_ECDSA_WITH_NULL_SHA ECDHE-RSA-AES256-SHA384 DHE-PSK-NULL-SHA TLS_RSA_PSK_WITH_NULL_SHA PSK-AES128-CBC-SHA TLS_DHE_PSK_WITH_AES_256_CBC_SHA384 TLS_FALLBACK_SCSV AESCCM8 derive_secret_key_and_iv DTLS_RECORD_LAYER_new dtls_wait_for_dry ssl3_get_record SSL_CTX_use_certificate SSL_enable_ct ssl_generate_session_id SSL_set_alpn_protos tls_construct_cke_rsa tls_parse_ctos_psk_kex_modes tls_prepare_client_certificate tls_process_server_done callback failed cert cb error connection type not set dane tlsa null data decryption failed or bad record mac http request inconsistent early 

OFFSET=0xc17547 TERM=dtls
CONTEXT=ES_128_CBC_SHA256 ADH-AES128-SHA256 ECDHE-RSA-NULL-SHA DHE-PSK-AES128-GCM-SHA256 TLS_PSK_WITH_AES_256_CBC_SHA384 RSA-PSK-AES128-CBC-SHA256 ECDHE-PSK-AES256-CBC-SHA384 DHE-DSS-ARIA256-GCM-SHA384 GOST12 COMPLEMENTOFDEFAULT kRSA add_key_share dtls1_preprocess_fragment dtls_construct_hello_verify_request ossl_statem_client13_write_transition set_client_ciphersuite ssl_ctx_make_profiles SSL_CTX_set_alpn_protos SSL_CTX_use_serverinfo_file SSL_SESSION_new tls_client_key_exchange_post_work tls_construct_client_certificate tls_construct_key_update tls_parse_stoc_psk tls_post_process_client_hello block ciph

OFFSET=0xc17561 TERM=dtls
CONTEXT=28-SHA256 ECDHE-RSA-NULL-SHA DHE-PSK-AES128-GCM-SHA256 TLS_PSK_WITH_AES_256_CBC_SHA384 RSA-PSK-AES128-CBC-SHA256 ECDHE-PSK-AES256-CBC-SHA384 DHE-DSS-ARIA256-GCM-SHA384 GOST12 COMPLEMENTOFDEFAULT kRSA add_key_share dtls1_preprocess_fragment dtls_construct_hello_verify_request ossl_statem_client13_write_transition set_client_ciphersuite ssl_ctx_make_profiles SSL_CTX_set_alpn_protos SSL_CTX_use_serverinfo_file SSL_SESSION_new tls_client_key_exchange_post_work tls_construct_client_certificate tls_construct_key_update tls_parse_stoc_psk tls_post_process_client_hello block cipher pad is wrong data betwe

OFFSET=0x9ed6b6 TERM=FINGERPRINT
CONTEXT=RtoSummaryStatisticsWindowSize FecQueueMediaSpecificEncoderMaxBufferLength ActualMatchHzWithInactiveFatalConditionDeterminationTimeUs ForceSetMatchCommandHz SuspendTimeoutMs Unknown error. Responded stun method. (ALLOCATE_SUCCESS_RESPONSE) FINGERPRINT REQUEST RP_APPROVAL RP_SYNC User-Agent: Mozilla/4.0 (compatible; UPnP/1.0; KONAMI) # [ WARNING ] FakeKeepAlive Switch Enaled. ## [ NTL WARNING ][ %d ] RecvFrom Error [ %s ][ %08x ] ## LastAnalyseTransport ${"CheckPktSize:":%d} ${"AllowRttPeakMsec:":%d} ${"AllowRttAvgMsec:":%d} ${"SamplingNr:":%d} ${"TimeoutMsec:":%d} ${"BandwidthLimit:":%d} ${"TotalSendSiz

OFFSET=0x9c6c0a TERM=P2P
CONTEXT=etworkIoReconnectServerTimeWaitMs DcTestQuickModeAppendResult DcTestForClientServerModeQualityForAntennaCalcMode DcTestForClientServerModeSuspendForBackgroundEnable RoutingTokenEnable OnlineSystem MultiplaySessionRecvThreadReceiveTimeoutUs P2P_ADHOC_BLE_LOW_LEVEL DelayBasedRecoveryEnable RtoEstimatorRttEwmaDeviationSafetyCoefficient FecQueueMediaSpecificRedundancy ActualMatchHzWithInactiveFatalConditionHzThreshold FrameRecoveryEnable Ignored the received data. (recvCallback is not set) Unauthorized. (error code = Requested stun method. (CHANNEL_BIND_REQUEST) platform_user_name USERNAME RP_RELAYE

OFFSET=0x9c6fe6 TERM=P2P
CONTEXT=UT ## HelperStatus ${"sendCnt":%d} %*[^ ] US use_parallel_download is_available_http2 use_network_request MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L5 MATCH_STOP_COUNT_SELF_BUF_EMPTY_MCACTIVE RECEIVE_IDLE_TIME TURN_QUALITY_RECENTLY_RTT_MEAN P2PTURNIO_TURN_RTT_VARIANCE LATENCY_TURN_RESOLVING_NAME_ANY_MAX LATENCY_TURN_RESOLVING_NAME_ANY_VARIANCE SEND_TO_NET_INFO_SEND_ERROR_COUNT DCTEST_ERROR_VALUE ABNORMALEND_REASON MODELNAME FPS_SETTING GAME_SERVER_STATS_SEND_ LATENCY_MODE_CONNECT_REVISION_CHECK MEMPEAK_MATCH_STEP IS_STAFF SURVEY_ID_2 %lu receipt_check_retry_interval_msec getTitle getProductId getO

OFFSET=0x9da7a4 TERM=P2P
CONTEXT=CONNECTED E_NOCHILD DETECT_NAT_ABORTED FREE_TURN_CHANNEL_BINDING_COMPLETE [ %s:%d ][ %d bytes ][ %04x ] HOST_ANY AS align_progress_abormal_end_timout_sec match_not_run_timeout_sec NETWORK_UP_COUNT TRANSPORT_RTT_ RECEIVED_VOICE_DATA_COUNT P2PTURNIO_TURN_RTT_MAX LATENCY_TURN_CONNECT_PEER_MEAN STATS_FORMAT LATENCY_MODE_CONNECT_QUALITY_TEST LATENCY_MODE_ANNTENA_PROCESS_CMD_GET_GAME_SESSION_CHECK_RES RTT_R_VARIANCE ()Lcom/android/billingclient/api/ProductDetails$OneTimePurchaseOfferDetails; win10_store_id CmdConnectGrpc onlineid network_delay_task CommunicationPrivilegeCheckTask enable_indicator_sta

OFFSET=0xa00c09 TERM=P2P
CONTEXT=c IPADDR_PEER MATCH_STOP_COUNT_BUF_EMPTY_BURST_L2_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L4_MCACTIVE IDELAY_BUF_SIZE_FOR_INPUT_DELAY_ RTT_ SELF_AUTOMOVE_COUNT SEND_COMMAND_MUST_NOT_DROP_COUNT_RECV NTL_PEER_STATUS TURN_QUALITY_LATEST_RTT P2PTURNIO_P2P_CONNECTING_TIME P2PTURNIO_RTT_VARIANCE_EVALUATION LATENCY_TURN_CONNECT_ANY_MIN SCORE_SITUATION LATENCY_NTL_PUNCHING_RETRY GAMRERELAY_MEASUARE_RESULT_AT_MATCHING MEMPEAK_RENDER_TARGET_POOL_SIZE MEMPEAK_MATCH_FLOW_KIND ADDRV6_CHANGED _DECODE_ SessionImplTry getOriginalJson getPricingPhases isProductDetailsSupported CmdWatchTurnAddressData.php Online

OFFSET=0xa00c13 TERM=P2P
CONTEXT=EER MATCH_STOP_COUNT_BUF_EMPTY_BURST_L2_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L4_MCACTIVE IDELAY_BUF_SIZE_FOR_INPUT_DELAY_ RTT_ SELF_AUTOMOVE_COUNT SEND_COMMAND_MUST_NOT_DROP_COUNT_RECV NTL_PEER_STATUS TURN_QUALITY_LATEST_RTT P2PTURNIO_P2P_CONNECTING_TIME P2PTURNIO_RTT_VARIANCE_EVALUATION LATENCY_TURN_CONNECT_ANY_MIN SCORE_SITUATION LATENCY_NTL_PUNCHING_RETRY GAMRERELAY_MEASUARE_RESULT_AT_MATCHING MEMPEAK_RENDER_TARGET_POOL_SIZE MEMPEAK_MATCH_FLOW_KIND ADDRV6_CHANGED _DECODE_ SessionImplTry getOriginalJson getPricingPhases isProductDetailsSupported CmdWatchTurnAddressData.php OnlineServiceEli

OFFSET=0xa00c27 TERM=P2P
CONTEXT=_BUF_EMPTY_BURST_L2_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L4_MCACTIVE IDELAY_BUF_SIZE_FOR_INPUT_DELAY_ RTT_ SELF_AUTOMOVE_COUNT SEND_COMMAND_MUST_NOT_DROP_COUNT_RECV NTL_PEER_STATUS TURN_QUALITY_LATEST_RTT P2PTURNIO_P2P_CONNECTING_TIME P2PTURNIO_RTT_VARIANCE_EVALUATION LATENCY_TURN_CONNECT_ANY_MIN SCORE_SITUATION LATENCY_NTL_PUNCHING_RETRY GAMRERELAY_MEASUARE_RESULT_AT_MATCHING MEMPEAK_RENDER_TARGET_POOL_SIZE MEMPEAK_MATCH_FLOW_KIND ADDRV6_CHANGED _DECODE_ SessionImplTry getOriginalJson getPricingPhases isProductDetailsSupported CmdWatchTurnAddressData.php OnlineServiceEligibilityCheckTask ET

OFFSET=0xa132d9 TERM=P2P
CONTEXT=anking TaskMatchCommissioner TaskSyncManager m_attackCoach m_oppCondition TaskSyncSideSelect SuspendedMatchResult CMD_CHECK_STRING CMD_GET_LIVEUPDATE_VERSION_INFO ERR_ALREADY_WAREHOUSE TaskGetRanking ChipShotControl AcrobaticFinishing ()[B P2P_ADHOC_UNKNOWN_HIGH_LEVEL TxBpsRecentBasicStatisticsMaxSize CorrectionRiseDeterminationTimeMsThresholdLow AppYieldIdleThreadResponseThreshold Xiaomi/M2103K19C|Xiaomi/M2101K7AG|Xiaomi/M2101K7AI P2pBufferCriticalConditionTimeMs TurnNetworkIoMigrateTimeWaitMsMax TurnNetworkIoEwmaPenaltySmoothCoef DcTestPingConnectionTimeoutMs DcTestQuickMode1NumPing DcTestOutli

OFFSET=0xa13708 TERM=P2P
CONTEXT=Transport >> BYPASS E_UHP_READY ALLOC_TURN_PORT_ABORTED PEER_REFLEXIVE FREE_C nativeOnReceivePurchasesUpdated load_timeout_sec SERVNAME_PEER HOP_COUNT_UDP_END_TEST MCLATENCY_ SELF_AUTOMOVE_COUNT_MCACTIVE TURN_QUALITY_BASESESSION_RTT_COUNT P2PTURNIO_P2P_RTT_Variance LATENCY_TURN_GET_TURN_ADDRESS_VARIANCE MANUFACTURER AWAY_SCORE DOWNLOAD_SERVER_STATS_SEND_ LATENCY_NTL_PUNCHING_TIME LATENCY_MODE_PRE_MENU_TEAM_DATA_SYNC SP_REGULATION_VALUE RX_LOSS_RATE_MAX ADDR_CHANGED RSSI_MAX RX_LOSS_RATE_R_MAX it->second: disable_kgs_unlock_on_cancelled (I)Ljava/lang/Object; getBasePlanId getSignature nativeOnAck

OFFSET=0xa13712 TERM=P2P
CONTEXT=>> BYPASS E_UHP_READY ALLOC_TURN_PORT_ABORTED PEER_REFLEXIVE FREE_C nativeOnReceivePurchasesUpdated load_timeout_sec SERVNAME_PEER HOP_COUNT_UDP_END_TEST MCLATENCY_ SELF_AUTOMOVE_COUNT_MCACTIVE TURN_QUALITY_BASESESSION_RTT_COUNT P2PTURNIO_P2P_RTT_Variance LATENCY_TURN_GET_TURN_ADDRESS_VARIANCE MANUFACTURER AWAY_SCORE DOWNLOAD_SERVER_STATS_SEND_ LATENCY_NTL_PUNCHING_TIME LATENCY_MODE_PRE_MENU_TEAM_DATA_SYNC SP_REGULATION_VALUE RX_LOSS_RATE_MAX ADDR_CHANGED RSSI_MAX RX_LOSS_RATE_R_MAX it->second: disable_kgs_unlock_on_cancelled (I)Ljava/lang/Object; getBasePlanId getSignature nativeOnAcknowledgeFi

OFFSET=0xa25588 TERM=P2P
CONTEXT=ETER_S_COMBATIVE_SPIRIT DATA_PARAMETER_S_VISIONARY_PASS PLAY_STYLE_NONE PLAY_STYLE_TARGET_MAN PLAY_STYLE_BOX_TO_BOX PLAY_STYLE_COVERING SKILL_CARD_HEADER SKILL_CARD_OUT_SIDE_LONG PLAYER_RARITY_GOLD REGION_EU PATHTOGLORY_1 SEARCHING DISCONN_P2P EVENT_CHALLENGE_CUSTOM MYCLUB_COMPE_COOP PITCH_CONDITION_DRY STADIUM_ASSET RANKING_EVENT_PARTICIPATION PANEL_MISSION_CONVERTED MATCH_WIN VSAI_EVENT_LIST CLEAN_SHEET WIN_UNDER_POWER_VS_COM WIN_GOAL_DIFFERENCE YELLOW_CARD CAN_START_MATCH TRAINING_SKILL_VETERAN_PLAYER PROMOTE_DIV_TWO_CUSTOM_LEAGUE TOTAL_WIN_CUSTOM_EVENT_COM GOAL_CUSTOM_EVENT_LEAGUE PROMOTE_DIV

OFFSET=0xa25d8d TERM=P2P
CONTEXT=vCompeEntry TaskEvCompeMainMenuCheckBeforeMatch TaskGetRequestedJoinRoomInfo custom_quick ERR_DIFFERENT_DATAVERSION ERR_NO_COACH CMD_GET_SESSION_ID TaskSaveScreenCapture LEVEL FlipFlap "user_name" "model" GetCommonInfoTask stadium_name ()J P2P CongestionControlWindowSizeLimitRecentBasicStatisticsMaxSize DequeueHzAccelerationMaxRate BufferKeeperEnableForPlatform MaxCorrection CorrectionFallDeterminationNotReadyForCommandDeltaCountThresholdLow m_asymmetricInputDelayTurnDisconnectStatusEnable TurnBufferCriticalConditionTimeAddConst TurnNetworkIoCheckDegradationThresholdRttCount DcTestForClientServer

OFFSET=0xa260ad TERM=P2P
CONTEXT=IsEnabledDisplayingLinesmanAndRefereeOnMobile unique_lock::lock: already locked ktc-0.0.0 Responded unexpected stun method. ( Responded stun method. (REFRESH_SUCCESS_RESPONSE) formation_json avator ETHERNET:OK 0.0.0.0 DATA OTHER_ADDRESS RP_P2P_HEADER CHANNEL MappingTestID Connection: Keep-Alive minor <?xml version="1.0"?> NewProtocol AddPinhole ## StunAgentDump isEnabled LOG_ACTIVE UhpFinalize E_HOSTDOWN E_MUTEX_SRCH HTTP_SESSION_ERROR UPNP_DELETE_PORT_FORWARDING_ERROR ALLOC_TURN_PORT_COMPLETE PEER_RELAYED command_auto_retry windows match_sync_failed_timeout_sec NSW ABNORMAL_END_FLAG HOP_COUNT_

OFFSET=0xa5eabb TERM=P2P
CONTEXT=WindowSize ChannelSendQueueRttEwmaSmoothCoefficient FecQueueParityRedundancy online_observe_playback_from_file Lifetime expired. (Lifetime = Unknown error. (error code = confirmed platform_kind CHANGE_ADDRESS RP_RAND_SEED RP_HEARTBEAT RP_P2P_SYNC NewRSIPAvailable ## [ NTL WARNING ][ %d ] GetPeerStatusEx Error [ pid %d ][ %s ][ %08x ] E_TURN_QUOTA_ERROR HTTP_SESSION_COMPLETE HTTP_SESSION_ABORTED START_UDP_HOLE_PUNCHING_COMPLETE START_UDP_HOLE_PUNCHING_PROGRESS ST_UHP SND ipv4only.arpa --/--[--:--:--.---](%02d:%02d:%02d) enabel_all_command_cancel INDICATOR_STATS_RECORDER Xbx giveup_byte_per_sec N

OFFSET=0xa5ecbb TERM=P2P
CONTEXT=02d:%02d:%02d) enabel_all_command_cancel INDICATOR_STATS_RECORDER Xbx giveup_byte_per_sec NATTYPE_PEER LINK_TYPE_PEERS IDELAY_BUF_SIZE_ TURN_OFF_COMMUNICATE_COUNT LATENCY_SESSION_ESTABLISH IP_ADDRESS_HOP_1_ICMP_BEGIN_TEST BACKGROUND_COUNTS P2PTURNIO_P2P_RTT_Max P2PTURNIO_RTT_MAX_EVALUATION HEADER GAME_RESULT GAME_SERVER_STATS_ MEMPEAK_WIDGET_HASH SURVEY_ID_0 RX_RLOSS_RATE_MAX LAST_SERVNAMEV6 pes22-game.cs.konami.net .txt -----BEGIN PUBLIC KEY----- MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEApC/7GywWS+F2J3/GcD2W QiRAhGOp7Y8VkMThCczHTd/ygGmuCSH0312p+9u0vZv/v5MyuAWK8Gm9jbZuDwAY uWKhgFCc4p9xoAMmLBzLo

OFFSET=0xa5ecc5 TERM=P2P
CONTEXT=02d) enabel_all_command_cancel INDICATOR_STATS_RECORDER Xbx giveup_byte_per_sec NATTYPE_PEER LINK_TYPE_PEERS IDELAY_BUF_SIZE_ TURN_OFF_COMMUNICATE_COUNT LATENCY_SESSION_ESTABLISH IP_ADDRESS_HOP_1_ICMP_BEGIN_TEST BACKGROUND_COUNTS P2PTURNIO_P2P_RTT_Max P2PTURNIO_RTT_MAX_EVALUATION HEADER GAME_RESULT GAME_SERVER_STATS_ MEMPEAK_WIDGET_HASH SURVEY_ID_0 RX_RLOSS_RATE_MAX LAST_SERVNAMEV6 pes22-game.cs.konami.net .txt -----BEGIN PUBLIC KEY----- MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEApC/7GywWS+F2J3/GcD2W QiRAhGOp7Y8VkMThCczHTd/ygGmuCSH0312p+9u0vZv/v5MyuAWK8Gm9jbZuDwAY uWKhgFCc4p9xoAMmLBzLoog81VWwQER

OFFSET=0xa5ecd1 TERM=P2P
CONTEXT=all_command_cancel INDICATOR_STATS_RECORDER Xbx giveup_byte_per_sec NATTYPE_PEER LINK_TYPE_PEERS IDELAY_BUF_SIZE_ TURN_OFF_COMMUNICATE_COUNT LATENCY_SESSION_ESTABLISH IP_ADDRESS_HOP_1_ICMP_BEGIN_TEST BACKGROUND_COUNTS P2PTURNIO_P2P_RTT_Max P2PTURNIO_RTT_MAX_EVALUATION HEADER GAME_RESULT GAME_SERVER_STATS_ MEMPEAK_WIDGET_HASH SURVEY_ID_0 RX_RLOSS_RATE_MAX LAST_SERVNAMEV6 pes22-game.cs.konami.net .txt -----BEGIN PUBLIC KEY----- MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEApC/7GywWS+F2J3/GcD2W QiRAhGOp7Y8VkMThCczHTd/ygGmuCSH0312p+9u0vZv/v5MyuAWK8Gm9jbZuDwAY uWKhgFCc4p9xoAMmLBzLoog81VWwQERu4QHRrH/p5z4

OFFSET=0xa716e1 TERM=P2P
CONTEXT=ER_STRONGER_HAND DATA_PARAMETER_S_RABONA DATA_PARAMETER_S_FORTRESS DATA_PARAMETER_S_AGGRESSIVE_SHOOTER PLAY_STYLE_DEFENSIVE_SB SKILL_CARD_ACCEL_BURST SKILL_CARD_CONTROL_LOOP_SHOT LEGENDARY MATERIAL_KEY_BG_004 NONE_CATEGORY EFOOTBALL_LEAGUE P2P_FAILED MATCHMENU ER_CANCEL ACHIEVEMENT LEAGUE_COM_MYCLUB NEWS_CATEGORY_E_FOOTBALL INFINITE_AGENT PURCHASE_BENEFITS COIN_BUNDLED_ITEM_REFUND_REVERSED PATHTOGLORY_10 CONDITION LEAGUE_AND_KNOCKOUT GORGEOUS_STADIUM_ROOF AMBASSADOR_PACK GOAL_CUSTOM_LEAGUE CHANGE_COACH PLAY_TEAM_STYLE_POSSESION PLAY_TEAM_STYLE_SIDE_ATTACK TRAIN_PLAYER PASS_CUT_CUSTOM_EVENT_PVP GO

OFFSET=0xa72124 TERM=P2P
CONTEXT=ax tw DlToStorageApi CmdHeartbeatGrpc.php prev_leave_foreground_time SERVER_UNAVAIL SendRequestNull ReceiveJClassNull (Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;JZ)V http/1.0 Server = CS_GIVE_UP_QUICKLY_LEVEL P2P_ADHOC_UNKNOWN_GIVE_UP_QUICKLY_LEVEL InputDelayBufferSizeForInputDelayRecentBasicStatisticsMaxSize PeriodicalBackupInterval BufferCriticalConditionBufferSizeThreshold CorrectionRiseWaitTimeMsThresholdHigh ListenerWorkerConfigPresetType DcTestQuickMode2UdpSendIntervalMs AccessLineTesterAutoTestTimeWaitTimeMs P2P_ADHOC_BTC DelayBasedLimiterLimitSafetyFactor Ch

OFFSET=0xa7225c TERM=P2P
CONTEXT=yRecentBasicStatisticsMaxSize PeriodicalBackupInterval BufferCriticalConditionBufferSizeThreshold CorrectionRiseWaitTimeMsThresholdHigh ListenerWorkerConfigPresetType DcTestQuickMode2UdpSendIntervalMs AccessLineTesterAutoTestTimeWaitTimeMs P2P_ADHOC_BTC DelayBasedLimiterLimitSafetyFactor ChannelDatagramLength ActualMatchHzWithInactiveIntervalUs MatchGageAdjustment MultiplayLlpChangeoverCommandThread ACTIVENETWORK:WIFI jp/konami/android/common/Reachability |->> [ %s ] ${"SendStunMsg":"[ %s ][ %s ] to [ %s:%d ][ %d bytes ]","tid":"%08x%08x%08x","act":"%s"} O573_FREE_CHANNEL MappingTestIC MappingTe

OFFSET=0xa84602 TERM=P2P
CONTEXT=egory match_event_list unlock_date block_uid DATA_PARAMETER_S_SCISSORS DATA_PARAMETER_S_BEAST_DRIVE PLAY_STYLE_WING_STRIKER SKILL_CARD_GK_ALERT ABILITY_BALL_CONTROL EULA_PRIVACY_NOTICE EULA_FUND_LAW_JAPAN TEAM_SELECT SAME_CLUB_TEAM DISCONN_P2P_NTL ER_MATCHING_RETRY MYCLUB_LOBBY_ROOM_MATCH_1VS1 MYCLUB_QUICK EVENT_MYCLUB_VSCOM RANKING_EVENT_MYCLUB WEATHER_TYPE_SNOW FREE_MATCH_PASS LOGIN_BONUS INQUIRY_APOLOGY FAIL_FULL IMPACT_SHOOT TRAINING_SKILL_MF_PLUS GOOGLE_PLAY JACKPOT_SCREEN GET_ACHIEVEMENT_PACK TOTAL_WIN_CUSTOM_EVENT_THEME NO_IMPROVEMENT FW_PRACTICE ERR_DATABASE ERR_BILLING_SERVER_MAINTENANCE

OFFSET=0xa84e75 TERM=P2P
CONTEXT=0Series\Source\Shared\pes\Game\Online\OnlineMode\Task\Matching\OnlineModeTaskMatchingOpp.cpp CMD_GET_EXHIBITION_ESPORTS_INFO ERR_CLIENT_SENDFAIL CMD_WATCH_NOTICE %s_f04_lim OneTouchPass WeightedPass AerialSuperiority 04 PESWE out of date ! P2P_ADHOC LatencyCriticalConditionQueueingSizeThreshold LatencyFatalConditionDeterminationTimeUs CorrectionRiseDeterminationTimeMs CorrectionRiseWaitTimeMs UERHIThreadPriority AppYieldUeThreadLowPriority CheckSocketDisabled TurnModeP2pSendIntervalMs TurnNetworkIoDegradedByDisconnectEnable MultiplaySessionStrategyIoBufferRecvSize FecQueueParityEncoderMaxBufferLe

OFFSET=0xabea90 TERM=P2P
CONTEXT=ppYieldLowPriorityTimeoutMs OPPO/CPH2127|OPPO/CPH2131|OPPO/CPH2133|OPPO/CPH2139 P2pModeTurnSendEnable TurnNetworkIoDegradedJudgementEnable AccessLineTesterAutoTestReceiveIdleTimeMsThreshold AccessLineTesterMode ObservePlaybackReadTimeoutMs P2P_ADHOC_BLE_HIGH_LEVEL P2P_ADHOC_LAN_HIGH_LEVEL P2P_ADHOC_LAN_GIVE_UP_QUICKLY_LEVEL ScalableTcpAlpha ParityDecoderEnablePadding Mobility forbidden. (error code = CMD_MATCH_SETTINGS revision param_check_sum SIGN CHANNELBIND %s:%s:%s SCANNING WANIPv6FirewallControl relayedAddress ALLOC_CHNL E_INVALID_ARGS E_INVAL E_DUP_ENDPOINT REFRESH_TURN_PORT_ERROR ALLOC_TU

OFFSET=0xabeaa9 TERM=P2P
CONTEXT=Ms OPPO/CPH2127|OPPO/CPH2131|OPPO/CPH2133|OPPO/CPH2139 P2pModeTurnSendEnable TurnNetworkIoDegradedJudgementEnable AccessLineTesterAutoTestReceiveIdleTimeMsThreshold AccessLineTesterMode ObservePlaybackReadTimeoutMs P2P_ADHOC_BLE_HIGH_LEVEL P2P_ADHOC_LAN_HIGH_LEVEL P2P_ADHOC_LAN_GIVE_UP_QUICKLY_LEVEL ScalableTcpAlpha ParityDecoderEnablePadding Mobility forbidden. (error code = CMD_MATCH_SETTINGS revision param_check_sum SIGN CHANNELBIND %s:%s:%s SCANNING WANIPv6FirewallControl relayedAddress ALLOC_CHNL E_INVALID_ARGS E_INVAL E_DUP_ENDPOINT REFRESH_TURN_PORT_ERROR ALLOC_TURN_PERMISSION_BINDING_ERR

OFFSET=0xabeac2 TERM=P2P
CONTEXT=131|OPPO/CPH2133|OPPO/CPH2139 P2pModeTurnSendEnable TurnNetworkIoDegradedJudgementEnable AccessLineTesterAutoTestReceiveIdleTimeMsThreshold AccessLineTesterMode ObservePlaybackReadTimeoutMs P2P_ADHOC_BLE_HIGH_LEVEL P2P_ADHOC_LAN_HIGH_LEVEL P2P_ADHOC_LAN_GIVE_UP_QUICKLY_LEVEL ScalableTcpAlpha ParityDecoderEnablePadding Mobility forbidden. (error code = CMD_MATCH_SETTINGS revision param_check_sum SIGN CHANNELBIND %s:%s:%s SCANNING WANIPv6FirewallControl relayedAddress ALLOC_CHNL E_INVALID_ARGS E_INVAL E_DUP_ENDPOINT REFRESH_TURN_PORT_ERROR ALLOC_TURN_PERMISSION_BINDING_ERROR FREE_TURN_PERMISSION_B

OFFSET=0xad1238 TERM=P2P
CONTEXT=rtise/020017/020017.png joinSessionResetConfirmAlert %s_b08 0000_m01_%d_%s DippingShot Marking G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineSystem\Api\OnlineSystemApiManagerver3.cpp pes-custom-encrypt verify HttpClientImpl2 P2P_LOW_LEVEL InputDelayBufferSizeStandardValueRecentBasicStatisticsMaxSize QueueReducesInMatchActiveMarginCoefficient AsymmetricInputDelayTurnDisconnectedModeEnable DoesBlockSocketError ChangeoverPeerReceiveIdleTimeMsThreshold DcTestPingTimeoutMs DcTestNumPing MultiplaySessionDaemonStatisticsIoBufferSize WebSocketClientConnectRetryIntervalMs DcTestWebSocketCli

OFFSET=0xae3ef0 TERM=P2P
CONTEXT=R FREE_TURN_PORT_ABORTED ALLOC_TURN_CHANNEL_BINDING_ERROR CHAOS DETECT_BAD canUseEthernet api_version ntl_impl_version users CONGESTION_CONTROL_BPS_ RECEIVED_FROM_UNKNOWN_PEER_COUNT RECEIVED_VOICE_DATA_LENGTH_INMATCH TURN_SESSION_RTT_COUNT P2PTURNIO_P2P_RX_LOSS_RATE LATENCY_TURN_GET_TURN_ADDRESS_MIN LATENCY_TURN_CONNECT_UDP_MAX SEND_TO_NET_INFO_MAX_SEND_INTERVAL SOC QUALITY_SETTING_FOR_STADIUM DOWNLOAD_SERVER_STATS_URL LATENCY_MODE_CONFIRMING_RESULT MEMPEAK_FLOW_HASH -o Source\Shared\pes\Game\Online\OnlineSystem\ServerDef\OnlineSystemServerKeywordDef.h CAMPAIGN getOriginalPrice ()Lcom/android/bi

OFFSET=0xae3efa TERM=P2P
CONTEXT=N_PORT_ABORTED ALLOC_TURN_CHANNEL_BINDING_ERROR CHAOS DETECT_BAD canUseEthernet api_version ntl_impl_version users CONGESTION_CONTROL_BPS_ RECEIVED_FROM_UNKNOWN_PEER_COUNT RECEIVED_VOICE_DATA_LENGTH_INMATCH TURN_SESSION_RTT_COUNT P2PTURNIO_P2P_RX_LOSS_RATE LATENCY_TURN_GET_TURN_ADDRESS_MIN LATENCY_TURN_CONNECT_UDP_MAX SEND_TO_NET_INFO_MAX_SEND_INTERVAL SOC QUALITY_SETTING_FOR_STADIUM DOWNLOAD_SERVER_STATS_URL LATENCY_MODE_CONFIRMING_RESULT MEMPEAK_FLOW_HASH -o Source\Shared\pes\Game\Online\OnlineSystem\ServerDef\OnlineSystemServerKeywordDef.h CAMPAIGN getOriginalPrice ()Lcom/android/billingclien

OFFSET=0xb1d5fd TERM=P2P
CONTEXT=esholdLow CorrectionRiseWaitTimeMsThresholdLow CorrectionRiseDeterminationNotReadyForCommandDeltaCountThresholdHigh NetworkQualityIndicatorTransportRttCountThreshold DcTestUtrTlsCaCertificate EnableUploadingMultiplayStatsAtGamePhaseChanged P2P_ADHOC_BTC_LOW_LEVEL P2P_ADHOC_UNKNOWN ChannelSendQueueRttEwmaDeviationSmoothCoefficient unique_lock::unlock: not locked multi_tactics_plan CMD_TEAM_SELECT is_guest_account EVEN_PORT REQUESTED_TRANSPORT DONT_FRAGMENT ATTR_EXTENSION O573_ID REFRESH CONNECTIONATTEMPT MappingTestIF ChannelRefresh NOT_SCANNED "upnpVersion":"%d.%d" NewExternalPort locale E_NOINIT

OFFSET=0xb1d615 TERM=P2P
CONTEXT=WaitTimeMsThresholdLow CorrectionRiseDeterminationNotReadyForCommandDeltaCountThresholdHigh NetworkQualityIndicatorTransportRttCountThreshold DcTestUtrTlsCaCertificate EnableUploadingMultiplayStatsAtGamePhaseChanged P2P_ADHOC_BTC_LOW_LEVEL P2P_ADHOC_UNKNOWN ChannelSendQueueRttEwmaDeviationSmoothCoefficient unique_lock::unlock: not locked multi_tactics_plan CMD_TEAM_SELECT is_guest_account EVEN_PORT REQUESTED_TRANSPORT DONT_FRAGMENT ATTR_EXTENSION O573_ID REFRESH CONNECTIONATTEMPT MappingTestIF ChannelRefresh NOT_SCANNED "upnpVersion":"%d.%d" NewExternalPort locale E_NOINIT E_NOROUTE E_MSGBROKEN U

OFFSET=0xb30671 TERM=P2P
CONTEXT=ityIndicatorManager CMDDeserializer SetRequest SetReadTimeoutMsec jp/konami/android/common/HttpDownloadImpl BufferKeeperEnable MaxKeepBufferSize WebSocketClientEnableIgnoreCertCnInvalid NetworkQualityTestAlwaysEnable MaxNumberOfPingRequest P2P_ADHOC_BTC_HIGH_LEVEL DelayBasedRecoveryHeavyCongestionFactor TransmissionSchedulerInterruptEnable LargeScaleMultiplayMatch30HzEnable CommandLackTimeoutMs NoMoveOperationTimeoutMsForStrikeArena Unknown internal state. (status = pf_play_history_key ACTIVENETWORK:ETHERNET XOR_MAPPED_ADDRESS_3489 RP_AMF_DATA PAD16 REF_ADDR ERROR_RESP MappingTestIII M-SEARCH * 

OFFSET=0xb30a02 TERM=P2P
CONTEXT=:%02d:%02d) giveup_msec nio system in_play SERVNAME NATTYPEV6_PEER COMMUNICATION_MODE RX_LOSS_RATE_ SEND_COMMAND_DROP_COUNT_BURST_L1 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L3_MCACTIVE MEMORY_PHYSICAL_AVAILABLE_KiB_ MEMORY_PHYSICAL_USED_KiB_ P2PTURNIO_TURN_RTT_MIN HTTP_WAITFORCONNECTIVITY RSSI_MIN RX_LOSS_RATE_MIN RX_LOSS_RATE_R_VARIANCE CmdGetProductList getProductType getSubscriptionOfferDetails getObfuscatedProfileId restartConnection canMakePayment can_buy_count pid_list retry_cmd_server_list SignInCheckTask GetModelName grpc.http2.initial_sequence_number grpc.workaround.cronet_compression ops_

OFFSET=0xb43a62 TERM=P2P
CONTEXT=rolIntervalMs MaxPayloadLength NetworkIoConnectionTimeoutUs TurnNetworkIoTcpConnectionTimeoutMs TurnNetworkIoDegradedLatencyRatio DcTestNumWorker NetworkTesterPingTimeoutMs PingRequestTimeoutUs LinkUpMode KeyExcahngeRetransmissionTimeoutUs P2P_ADHOC_WIFIDIRECTLAN_LOW_LEVEL P2P_ADHOC_LAN direct_online_turn_mode NetworkQualityIndicator ps f2p RESPONSE_ADDRESS RP_SYNC_POINT |->> [ %s ][ %d ] URLBase TurnInitializedNatType RevokeConnectivity uds E_NOMEM E_NOTFOUND E_UPNP_DEVICE_NOT_FOUND E_TURN_NOT_AVAILABLE UPNP_DISCOVERY_FULL_COMPLETE START_UDP_HOLE_PUNCHING_ADVICE_CANCEL_HAIRPIN jnihelper ] is a

OFFSET=0xb43a84 TERM=P2P
CONTEXT=workIoConnectionTimeoutUs TurnNetworkIoTcpConnectionTimeoutMs TurnNetworkIoDegradedLatencyRatio DcTestNumWorker NetworkTesterPingTimeoutMs PingRequestTimeoutUs LinkUpMode KeyExcahngeRetransmissionTimeoutUs P2P_ADHOC_WIFIDIRECTLAN_LOW_LEVEL P2P_ADHOC_LAN direct_online_turn_mode NetworkQualityIndicator ps f2p RESPONSE_ADDRESS RP_SYNC_POINT |->> [ %s ][ %d ] URLBase TurnInitializedNatType RevokeConnectivity uds E_NOMEM E_NOTFOUND E_UPNP_DEVICE_NOT_FOUND E_TURN_NOT_AVAILABLE UPNP_DISCOVERY_FULL_COMPLETE START_UDP_HOLE_PUNCHING_ADVICE_CANCEL_HAIRPIN jnihelper ] is already registered! ANDROID Windows

OFFSET=0xb43cff TERM=P2P
CONTEXT=_COUNT_BURST_L5 SEND_COMMAND_DROP_COUNT_BURST_L4_MCACTIVE SELF_AUTOMOVE_COUNT_BURST_L2 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L4 RECEIVED_COMMAND_COUNT RECEIVED_VALID_COUNT SENT_VOICE_DATA_COUNT_INMATCH AWAY_TEAM_ID_NO TURN_SESSION_RTT_EWMA P2PTURNIO_P2P_RTT_Mean TURN_TCP MAIN_THREAD_ELAPSED_SINCE_LAST_UPDATED VALUE need_root_box_warn_due_to_age CmdSendNotice ticket turn_server_list SendAdjustParamTask 10BASE_HALF WIMAX DisableBroadcasting grpc.http2.write_buffer_size grpc.keepalive_permit_without_calls grpc.xds_locality_retention_interval_ms plugin_credentials grpc_channel_arguments G:/PES22HC/De

OFFSET=0xb43d09 TERM=P2P
CONTEXT=ST_L5 SEND_COMMAND_DROP_COUNT_BURST_L4_MCACTIVE SELF_AUTOMOVE_COUNT_BURST_L2 MATCH_STOP_COUNT_SELF_BUF_EMPTY_BURST_L4 RECEIVED_COMMAND_COUNT RECEIVED_VALID_COUNT SENT_VOICE_DATA_COUNT_INMATCH AWAY_TEAM_ID_NO TURN_SESSION_RTT_EWMA P2PTURNIO_P2P_RTT_Mean TURN_TCP MAIN_THREAD_ELAPSED_SINCE_LAST_UPDATED VALUE need_root_box_warn_due_to_age CmdSendNotice ticket turn_server_list SendAdjustParamTask 10BASE_HALF WIMAX DisableBroadcasting grpc.http2.write_buffer_size grpc.keepalive_permit_without_calls grpc.xds_locality_retention_interval_ms plugin_credentials grpc_channel_arguments G:/PES22HC/Dev-600Serie

OFFSET=0xb55aa3 TERM=P2P
CONTEXT=07G|samsung/SM-A307GN|samsung/SM-A307GT ChangeoverToTurnReceiveIdleTimeMsThreshold TurnNetworkIoRecentlyRttMaxSize DcTestForClientServerModeMaxRetryTimeoutMs WebSocketClientDisableVerifyHost AccessLineTesterNetworkQualityDegradeCoefficient P2P_ADHOC_WIFIDIRECTLAN_GIVE_UP_QUICKLY_LEVEL P2P_ADHOC_LAN_LOW_LEVEL wss:// G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineSystem\Multiplay\SessionStrategy\OnlineSystemMultiplaySessionStrategyP2pFullMeshWithTurn.cpp ] RP_JSON_DATA SEQ MappingTestIB FilteringTestII Allocate GetNonce |->> [ %s ][ %d ][ %s ] extra E_OK E_STUN_TEST_ERROR E_MUTEX_IN

OFFSET=0xb55ad1 TERM=P2P
CONTEXT=overToTurnReceiveIdleTimeMsThreshold TurnNetworkIoRecentlyRttMaxSize DcTestForClientServerModeMaxRetryTimeoutMs WebSocketClientDisableVerifyHost AccessLineTesterNetworkQualityDegradeCoefficient P2P_ADHOC_WIFIDIRECTLAN_GIVE_UP_QUICKLY_LEVEL P2P_ADHOC_LAN_LOW_LEVEL wss:// G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineSystem\Multiplay\SessionStrategy\OnlineSystemMultiplaySessionStrategyP2pFullMeshWithTurn.cpp ] RP_JSON_DATA SEQ MappingTestIB FilteringTestII Allocate GetNonce |->> [ %s ][ %d ][ %s ] extra E_OK E_STUN_TEST_ERROR E_MUTEX_INVAL FREE_TURN_CHANNEL_BINDING_ABORTED ro.build

OFFSET=0xb55d52 TERM=P2P
CONTEXT=ion_not_connected_timeout_sec SERVNAMEV6 PLATFORM_PEERS NUM_GUESTS_END_MATCH MCDEQUEUEHZ_RATE_ MATCH_STOP_COUNT_BUF_EMPTY TURN_QUALITY_DEGRADATION_RATE TURN_SESSION_RESPONSE_WAITING_TIME TURN_SESSION_RTT_MAX TURN_SESSION_ATTRIBUTE_SOFTWARE P2PTURNIO_RX_LOSS_RATE_EVALUATION DCTEST_OPTIMUM_REGION GAME_SERVER_STATS_RECV_ LATENCY_MODE_CONNECT_WAIT_SOCKET LATENCY_MODE_ANNTENA_USER_DATA_SYNC ] 7.16 PlatformSessionManager isAcknowledged nativeOnBuyFinished iab currency nsw_item_id CmdAuthSteam address_data_size MOBILE_3G MOBILE_4G MultiStatsUploader enable_indicator_stats tue wed GetGPUModelName grpc.

OFFSET=0xb68e29 TERM=P2P
CONTEXT=eUserCompe isProceed CMD_VERIFY_USER_CAN_BUY TaskUserActionKickUserCompe EVENT_ML FirstTimeShot LongThrows Interception 01 16 20 /Game/Assets/ui/Data/Thumbnail/Skill/Skill_ Def_Online_gRPC_server_port dec0 , Others = NetworkAccessLineTest P2P_HIGH_LEVEL MatchCommandDequeueHzRateRecentBasicStatisticsMaxSize DequeueHzAccelerationMarginBufferSize MatchControlAlgorithm MinKeepBufferSize CorrectionFallDeterminationNotReadyForCommandDeltaCount AsymmetricInputDelayTurnLimitEnable AsymmetricInputDelayTurnSuddenChangeEnable EnableManufactureModelNamePresetType Dscp ScrambleEnable TcpFallbackEnable DcTest

OFFSET=0xb7bfb2 TERM=P2P
CONTEXT=ectionRiseDeterminationTimeMsThresholdHigh CorrectionFallThresholdHigh EnableSocketErrorLog TurnBufferCriticalConditionTimeMsMax DcTestUdpStickyAddressLongTimeoutMs DcTestForClientServerModeIntervalMs DcTestWebSocketClientDisableVerifyPeer P2P_ADHOC_WIFIDIRECTLAN_HIGH_LEVEL FastTcpSrttSmoothCoefficient ChannelSendQueueBufferLength MultiplaySessionRecv DONE_ONE_PUNCHING %d:%d; SOURCE_ADDRESS ALTERNATE_SERVER RP_HOST_ADDRESS USER_ID O573_CR_RESP RP_EXIT |->> [ %s ][ %s ] SERVER serviceType "buildUrl":"" EventHandler [ ret >> %3d ][ msg >> %s ] ## NTLInfo ${"libVer":"%s%s"} ${"uid":"%08x%08x%08x%08

OFFSET=0xb7c232 TERM=P2P
CONTEXT={"upnp":[ 255.255.255.255 BAD_STATUS_CODE enable_gateway_timeout is_enable_for_match RX_RLOSS_RATE_MEAN_NPI MATCH_STOP_MAX_ROLLING_COUNT_BUF_EMPTY_IV1_MCACTIVE SEND_COMMAND_MUST_NOT_DROP_COUNT_SEND HOME_TEAM_ID_NO TURN_SESSION_RTT_VARIANCE P2PTURNIO_TURN_RX_LOSS_RATE LATENCY_TURN_RESOLVING_NAME_ANY_MEAN CMD_FAILED_COUNT_HTTP CMD_FAILED_COUNT_GRPC PLATFORM IDELAY_MEAN_MCACTIVE it->first: scheme getOfferId (Lcom/android/billingclient/api/Purchase;)Ljava/lang/String; nativeOnGetInventoryFinished android_id obfuscated_account_id need_refund_reversed_detect_notice bonus_coin CmdSendSessionId.php use_h

OFFSET=0xba30b4 TERM=P2P
CONTEXT=COMPLETE ,%s JNIHVoidMethodV ntl_ethernet_portselectpolicy gdk OSVERSION_PEERS SELF_AUTOMOVE_COUNT_BURST_L5 SELF_AUTOMOVE_COUNT_BURST_L1_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L1 RECEIVE_UNKNOWN_ERROR_COUNT MEMORY_VIRTUAL_AVAILABLE_KiB_ P2PTURNIO_TURN_RTT_MEAN P2PTURNIO_RTT_MIN_EVALUATION time, ping_mean, ping_variance, ping_min, ping_max, pes_hz_mean, pes_hz_variance, pes_hz_min, pes_hz_max, ue_hz_mean, ue_hz_variance, ue_hz_min, ue_hz_max, CURRENT_DIVISION LOW LATENCY_MODE_ANNTENA_POLLING_CMD_GET_GAME_SESSION_CHECK_RES LATENCY_MODE_PRE_MENU_READY_ALL_PLAYER MEMPEAK_TEXTURE_STREAM_POOL_SIZE

OFFSET=0xba30cc TERM=P2P
CONTEXT=hodV ntl_ethernet_portselectpolicy gdk OSVERSION_PEERS SELF_AUTOMOVE_COUNT_BURST_L5 SELF_AUTOMOVE_COUNT_BURST_L1_MCACTIVE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L1 RECEIVE_UNKNOWN_ERROR_COUNT MEMORY_VIRTUAL_AVAILABLE_KiB_ P2PTURNIO_TURN_RTT_MEAN P2PTURNIO_RTT_MIN_EVALUATION time, ping_mean, ping_variance, ping_min, ping_max, pes_hz_mean, pes_hz_variance, pes_hz_min, pes_hz_max, ue_hz_mean, ue_hz_variance, ue_hz_min, ue_hz_max, CURRENT_DIVISION LOW LATENCY_MODE_ANNTENA_POLLING_CMD_GET_GAME_SESSION_CHECK_RES LATENCY_MODE_PRE_MENU_READY_ALL_PLAYER MEMPEAK_TEXTURE_STREAM_POOL_SIZE %d_%d RX_RLOSS_RATE_R_M

OFFSET=0xbc91b4 TERM=P2P
CONTEXT=A_PARAMETER_FREE_KICK_TYPE DATA_PARAMETER_S_PIN_POINT_CROSS DATA_PARAMETER_S_PK_KICKER SKILL_CARD_SCISSORS_SKILLS SKILL_CARD_HEEL_TRICK SKILL_CARD_RABONA SKILL_CARD_LOW_PUNT_KICK SKILL_CARD_GK_RUSH_OUT TEAM_STYLE_CATEGORY EAGLE_EYE DEGRADE_P2P 1ST_15MIN ER_SERVER_GONE EVENT_MYCLUB CONDITION_TERRIBLE SMART_OFF COOP_VS_ANOTHER_ROOM TEAM_STYLE_LONG_COUNTER E_FOOTBALL_POINT STRIKE_ARENA_REWARD CUSTOM_LEAGUE_COM_PHASE AGENT_NORMAL SCORE_GOAL PATHTOGLORY_08 ACHIEVEMENT_EX COLLECTION KNOCKOUT_ONLY OPENING_BIGTIME REVIVAL_TWO AGENT_TARGET TOTAL_GOAL_CUSTOM_LEAGUE WIN_CUSTOM_EVENT_COM GOAL_CUSTOM_EVENT_PV

OFFSET=0xbc9a2e TERM=P2P
CONTEXT=_lim %s_m01_%ld_max CutBehindTurn GKLongThrows AcrobaticClearance 12 cn G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineSystem\Auth\OnlineSystemAuthUserIdStorage.cpp JSON_PARSE_ERROR ExecuteFindClass MatchesManager , Own = CS P2P_GIVE_UP_QUICKLY_LEVEL MatchCommandLatencyRecentBasicStatisticsMaxSize AsymmetricInputDelayThreshold AppYieldIdleThreadIntervalMs CmpNetworkIoVersion NameResolverTimeoutMs TurnNetworkIoQuickPingIntervalMs DcTestEraseUdpStickyFailure DcTestVersion AccessLineTesterMaxTtl P2P_ADHOC_BLE_GIVE_UP_QUICKLY_LEVEL FastTcpAlpha FastTcpGamma ChannelSchedulerPriority Upd

OFFSET=0xbc9b3f TERM=P2P
CONTEXT=mmandLatencyRecentBasicStatisticsMaxSize AsymmetricInputDelayThreshold AppYieldIdleThreadIntervalMs CmpNetworkIoVersion NameResolverTimeoutMs TurnNetworkIoQuickPingIntervalMs DcTestEraseUdpStickyFailure DcTestVersion AccessLineTesterMaxTtl P2P_ADHOC_BLE_GIVE_UP_QUICKLY_LEVEL FastTcpAlpha FastTcpGamma ChannelSchedulerPriority Update connection ID. ( Responded stun method. (ALLOCATE_ERROR_RESPONSE) ACTIVENETWORK:CELLULAR RETRY_PUNCHING ::%s0 BINDING RP_ENTRY MappingTestIG ${"%s":"[ %s ][ %s ] from [ %s ][ %d bytes ]","tid":"%08x%08x%08x"} md5 Cache-Control: no-cache Pragma: no-cache deviceType Devi

OFFSET=0xbef372 TERM=P2P
CONTEXT=ectionFallDeterminationTimeMs CorrectionFallDeterminationTimeMsThresholdLow AsymmetricInputDelayTurnDelayDisconnect AppYieldCpuOnlineRateThreshold MultiplaySessionDaemonStatisticsIoBufferEnable ObservePlaybackBufferLength TimeWaitTimeoutMs P2P_ADHOC_WIFIDIRECTLAN P2P_ADHOC_BTC_GIVE_UP_QUICKLY_LEVEL P2P_ADHOC_BLE DelayBasedLimiterHeavyCongestionFactor SlowdownDetectionInFastForwardEnable MatchCommandBufferingControlType InitializationTimeoutMs Closed. (ConnectionId = Requested stun method. (ALLOCATE_REQUEST) member_change_json matchplan_settings_json CELLULAR:OK NTL history PermissionData ERROR_C

OFFSET=0xbef38a TERM=P2P
CONTEXT=imeMs CorrectionFallDeterminationTimeMsThresholdLow AsymmetricInputDelayTurnDelayDisconnect AppYieldCpuOnlineRateThreshold MultiplaySessionDaemonStatisticsIoBufferEnable ObservePlaybackBufferLength TimeWaitTimeoutMs P2P_ADHOC_WIFIDIRECTLAN P2P_ADHOC_BTC_GIVE_UP_QUICKLY_LEVEL P2P_ADHOC_BLE DelayBasedLimiterHeavyCongestionFactor SlowdownDetectionInFastForwardEnable MatchCommandBufferingControlType InitializationTimeoutMs Closed. (ConnectionId = Requested stun method. (ALLOCATE_REQUEST) member_change_json matchplan_settings_json CELLULAR:OK NTL history PermissionData ERROR_CODE XOR_RELAYED_ADDRESS 

OFFSET=0xbef3ae TERM=P2P
CONTEXT=eMsThresholdLow AsymmetricInputDelayTurnDelayDisconnect AppYieldCpuOnlineRateThreshold MultiplaySessionDaemonStatisticsIoBufferEnable ObservePlaybackBufferLength TimeWaitTimeoutMs P2P_ADHOC_WIFIDIRECTLAN P2P_ADHOC_BTC_GIVE_UP_QUICKLY_LEVEL P2P_ADHOC_BLE DelayBasedLimiterHeavyCongestionFactor SlowdownDetectionInFastForwardEnable MatchCommandBufferingControlType InitializationTimeoutMs Closed. (ConnectionId = Requested stun method. (ALLOCATE_REQUEST) member_change_json matchplan_settings_json CELLULAR:OK NTL history PermissionData ERROR_CODE XOR_RELAYED_ADDRESS O573_CR_XADDR SEND UHP_CONNECT ST UD

OFFSET=0xbef8e6 TERM=P2P
CONTEXT=S_ SELF_AUTOMOVE_COUNT_BURST_L1 MATCH_CONTROL_SESSION_SEND_HEADER_DELTATIME_MS_ RECEIVED_COUNT RECEIVED_VOICE_DATA_LENGTH IP_ADDRESS_HOP_2_ICMP_BEGIN_TEST TURN_QUALITY_DEGRADATION_RTT_MEAN TURN_QUALITY_DEGRADATIONSESSION_TRANSPORT_RTT_MEAN P2PTURNIO_P2P_RTT_Min LATENCY_TURN_RESOLVING_NAME_MIN 0x%x CS_SERVER_ADDRESS LATENCY_NTL_PUNCHING_PROCESS_ON_SUCCESS LATENCY_MODE_CONNECT LATENCY_MODE_MATCHING_CMD_GET_SERVER_ENV LATENCY_MODE_SESSION_PROCESS_CMD_GET_GAME_SESSION MEMPEAK_GAME_STATE_MISC_BITS V6_TCP_SOCKET_ERROR ACTUAL_MATCH_HZ_MEAN LAST_SERVNAME RX_RLOSS_RATE_R_VARIANCE 

OFFSET=0xbef8f0 TERM=P2P
CONTEXT=TOMOVE_COUNT_BURST_L1 MATCH_CONTROL_SESSION_SEND_HEADER_DELTATIME_MS_ RECEIVED_COUNT RECEIVED_VOICE_DATA_LENGTH IP_ADDRESS_HOP_2_ICMP_BEGIN_TEST TURN_QUALITY_DEGRADATION_RTT_MEAN TURN_QUALITY_DEGRADATIONSESSION_TRANSPORT_RTT_MEAN P2PTURNIO_P2P_RTT_Min LATENCY_TURN_RESOLVING_NAME_MIN 0x%x CS_SERVER_ADDRESS LATENCY_NTL_PUNCHING_PROCESS_ON_SUCCESS LATENCY_MODE_CONNECT LATENCY_MODE_MATCHING_CMD_GET_SERVER_ENV LATENCY_MODE_SESSION_PROCESS_CMD_GET_GAME_SESSION MEMPEAK_GAME_STATE_MISC_BITS V6_TCP_SOCKET_ERROR ACTUAL_MATCH_HZ_MEAN LAST_SERVNAME RX_RLOSS_RATE_R_VARIANCE 

OFFSET=0xc023f1 TERM=P2P
CONTEXT= CMD_AUTH_XSTS ERR_SKILL_DOES_NOT_EXIST CustomStadium2.bin SendJoinRoomRequest SubTaskUserCompeGetUserCompeInfo TaskSetUserName DIVISION Captaincy 23 ERR_CANCELED %06d send callback failed Def_Online_gRPC_insecure : { GetRequestReceiveTime P2P_ADHOC_UNKNOWN_LOW_LEVEL BufferWarningLv2ConditionBufferSizeThreshold ScrambleCode TurnNetworkIoDegradedByLatencyEnable ConnectMainWaitTimeMS DcTestRecvTimeoutMs NetworkQualityIndicatorUpdateIntervalMs WebSocketClientDisableVerifyPeer NetworkTesterBaseRttMeasurementTimeMs RttSummaryStatisticsWindowSize ProtocolChannel Responded stun method. (CHANNEL_BIND_SUC

OFFSET=0xc15c26 TERM=P2P
CONTEXT=EEPALIVE PEER_HOST pes_thread_onsys_manager total_timeout IOS android ps5 XBX onmode NATTYPE MATCH_STOP_COUNT_BUF_EMPTY_BURST_L3_MCACTIVE MATCH_STOP_MAX_ROLLING_COUNT_BUF_EMPTY_IV3_MCACTIVE AT_OFFENCE_BACKGROUND_COUNTS TURN_CHANGEOVER_TIME P2PTURNIO_RTT_MEAN_EVALUATION PING_ANTENNA_LEVEL END_REASON OPERATION_TYPE CS_SERVER_NAME GAME_SERVER_STATS_URL TRANSPORT_RTT_MAX CmdConsumeItem consumeItem nativeOnGetBillingConfigFinished pes_receipt CmdSendNotice.php wait_msec_cmd_turn_address on_sys_common_thread_pool fri statvfs error grpc.max_connection_age_ms grpc.enable_channelz G:/PES22HC/Dev-600Series

OFFSET=0x2ecda4 TERM=relay
CONTEXT=tr M2TSD_IsConformable M2TSD_SetErrFn M2TSD_SetPesSw M2TSD_SetTsMapFn M2TSD_version_str m2tsd_cnt_discontinuity_indicator m2tsd_cnt_duplicate m2tsd_cnt_err_continuity_counter m2tsd_cnt_transport_error_indicator m2tsd_insj m2tsd_outsj m2tsd_relaysj SJCRS_Finish_nstm SJCRS_Init_nstm SJCRS_Lock_nstm SJCRS_Unlock_nstm sjcrs_lvl_nstm sjcrs_msk_nstm SJERR_CallErr_nstm SJRBF_CalcWorkSize_nstm SJRBF_CreateHndl_nstm SJRBF_Destroy_nstm SJRBF_DisableCs_nstm SJRBF_EntryErrFunc_nstm SJRBF_EntryPutFunc_nstm SJRBF_Error_nstm SJRBF_GetBufPtr_nstm SJRBF_GetBufSize_nstm SJRBF_GetChunk_nstm SJRBF_GetNumData_nstm SJRB

OFFSET=0x9d90fc TERM=relay
CONTEXT=SubTitle Launch TrainingMoveBall PanelMission_2 TaskConnectGameService CmdSendReport CmdSearchUser CmdGetEventCompeGroupStageDraw CmdGetMyclubEntryInfo CmdGetGpShopItemList CmdGetEulaAreaListSeasonUpdate CmdGetGameresultList CmdSetLocalGamerelayList CmdChangeGamephase CmdGetKonamiidFunctionalBlockade is_deleted team_id uniform_info breakdown_list image_id rev_result link_list offense_com_level color_b campaign_id is_acquired initial_base_national_team_id is_campaign stadium_asset_name text_str is_repeat is_limited reward_point_list life_info conditions_type_2 displayed is_attention_demo first_clear

OFFSET=0x9ffc3d TERM=relay
CONTEXT=istory PeriodFreeKey CanDispSeeMore NoticeNo PlayerProgression_1 Analyst_1 NewFormation_1 ,"removeFunc": CmdGetEnterEventCompe CmdDeleteRoomGuest CmdSellMyclubCoach CmdBuyMyclubScoutPlayer CmdGetCoinUseInfo CmdSetSeasonUpdateInfo CmdSetGamerelayQuality CmdGetKidParentalAgreementStatus is_clear issuer_id bonus_use_count present_list after_paid_coin entity_id pack_num collection_info pk_flag exp_total away_score special_emmission_rate away_team_id condition_cpu_level set_piece_taker retry_num exTime fans period detail_info bingo_link_info squad eula_privacy_notice rank_to high_score recommend_kind sq

OFFSET=0xa00319 TERM=relay
CONTEXT= added_coin_list agent_bonus_list event_match_label puzzles_per_page CmdGetServerEnv.php CMD_GET_STADIUM_DATA konamiid_age_kind CMD_GET_USER_INQUIRY_INFO CMD_GET_VOID_LIST CMD_JOIN_GAME_MODE livedata_version is_alert_eFpoint CmdSetLocalGamerelayList.php away smart_assist feint_type squad_data_away file_hash_list MYCLUB_CHALLENGE CmdSellMlEventPlayer.php CmdSetMlEventSquadInfo.php CmdGetLeagueComInfo.php CmdAddRoomGuest.php is_all_draft CMD_SET_MYCLUB_BRING_UNIFORM CmdSetMyclubSpecialDreamSquadInfo.php squad_base_team_list BUY_BY_VOID_TICKET CmdUseMyclubCareerplan.php skill_training_result CMD_EXCHA

OFFSET=0xa4b06b TERM=relay
CONTEXT= challenge_list onsys_opt command_retry_num title_image_info topbanner_autoscroll_interval_msec billboard_country_list CmdGetSurveyInfo.php country_status is_link_kid faul offense_positioning coach_data play_data CMD_SET_USER_EULA_INFO gamerelay_measure_result CMD_UPDATE_TERMS_TO_SERVICE CmdGetEventMissionAiMatchList.php CmdGetEventCompeGroupStageDraw.php CMD_BUY_ML_EVENT_LIFE SE_DIALOG_RELEASED room_kind is_exist_request_to_join CMD_RETURN_ROOM CmdDeleteMyclubSkill.php CMD_DELETE_MYCLUB_SQUAD base_gameplayer_id CMD_USE_MYCLUB_CAREERPLAN auto_item_list CmdUseMyclubStandardDraft.php CmdGetVotingInfo

OFFSET=0xa8486f TERM=relay
CONTEXT=ALREADY_HAVE ERR_NOT_READY ERR_NO_REWARD ERR_TRANS_LINKED_BY_ME ERR_GAME_RESULT_NOT_FOUND ERR_INVALID_REDEEM_CODE is_recv_mailbox injury_gameplayer_id maintenance_time CmdCreateUser.php is_in_eea CONTRACT_COACH REFUND_ITEM_BUNDLED_COIN gamerelay quality_list is_all CmdGetIsAccountLink.php steam_id event_ch_type item_kind is_need_ranking_changed_alert ai_division analyst_main_info CmdGetMannerWarn.php CmdGetMatchingResult.php puzzle_flavor_text challenge_code ip_state_code slowdown_judgment_threshold_list survey_info is_disable_sharing coop_score advice_info_match ignore_receipt_error ad_placement C

OFFSET=0xa97bd6 TERM=relay
CONTEXT=me_zone CmdGetStrikeArenaInfo.php CMD_SET_STRIKE_ARENA_COSTUME d_user_compe_id compe_format_type enable_entry_limit relationship CMD_SET_FAVORITE_PLAYER CmdRequestKidParentalAgreement.php NORMAL_4 CMP CgkI2KWEy_UIEAIQUQ TaskEvCompeLocalGamerelay Error!! Please restart application. TaskLeagueRoot TaskLobbyLeaveRoom Online/Lobby/ProcLobbyRoomCheckGoMatchForceProceed TaskLoginSubInputCountryFlow TaskAnalystMatchAdviceManager TaskGameQueueProcessor G:\PES22HC\Dev-600Series\Source\Shared\pes\Game\Online\OnlineMode\Task\Match\OnlineModeTaskMultiplaySession.cpp matching_polling_interval_msec faital_error

OFFSET=0xaa963d TERM=relay
CONTEXT=/constant/stadium/demoarea_st066.json DevelopData/common/match/constant/tutorialConsole/Beginner_Crossing.json L_mic_1C turnStepMove airRegistNormal boundToRotationSpeedMinY nonSpinTopRiseDecRate rollToSpeedMaxRoll isTargetKeepPlayerEnable relayParam assist_over2 many_save freekickDebug pauseRestartMoveTime setupNo p0_speed_average limitFrontX distForGageMax passDistMaxThrough accRateDif180 decMinSpeedR circleDist positionAdjustEnable normalShootGageMid40 adjustFrameSpaceRun manualPassSpeedAdjust passFrameMargin targetDistMin foot hitFrameBase offsetPos_Dash_Dash offsetPos_Run_Idle offsetPos_Run_Ru

OFFSET=0xaaac6f TERM=relay
CONTEXT=oint special_skill total team_tactics acquisition_date is_completed is_transfer is_skip_match CONDITION_RANDOM my_platform observer_capacity is_coop_vs_com_single is_squad_enable eula_myclub_japan pt_main_rest_point bonus_info is_local_gamerelay collabo_kind pt_setting_pattern pt_theme_bonus useable_compe_list es_detail point_promoted eula_ip_country_a3 dont_sell slot_num DATA_PARAMETER_S_CHAPEAU DATA_PARAMETER_S_OUT_SIDE_LONG DATA_PARAMETER_S_BULLET_HEADER PLAY_STYLE_NUMBER_10 SKILL_CARD_FLIP_FLAP_SKILLS SKILL_CARD_SOMBRERO SKILL_CARD_DROP_SHOT SKILL_CARD_GK_COACHING ABILITY_SHOT ABILITY_KICKING_P

OFFSET=0xaab28f TERM=relay
CONTEXT=_bg_image_name_list short_demo_limit_online use_league_category CMD_GET_VSCOM_GAME_RESULT is_stun_keep_alive_failed is_background_timeout ex_flag defense_positioning AGENT CmdRequestUserDelete.php CmdSendRecruitCode.php CMD_SEND_REPORT gamerelay_list setplay_fk_long market_value auto_offsidetrap bring_uniform div uniform_list_home CMD_GET_EVENT_SELF_RECORD difference_squad_data is_out_of_countries CmdSendMlEventProceed.php CmdSendFriendRequest.php enable_room_id CMD_INHERIT_MYCLUB_GAMEPLAYER gain_gp skip_check_team_name special_squad_data is_boss_match CMD_GET_STRIKE_ARENA_INFO is_sub_owner CmdGetR

OFFSET=0xabeb9b TERM=relay
CONTEXT=P_ADHOC_LAN_HIGH_LEVEL P2P_ADHOC_LAN_GIVE_UP_QUICKLY_LEVEL ScalableTcpAlpha ParityDecoderEnablePadding Mobility forbidden. (error code = CMD_MATCH_SETTINGS revision param_check_sum SIGN CHANNELBIND %s:%s:%s SCANNING WANIPv6FirewallControl relayedAddress ALLOC_CHNL E_INVALID_ARGS E_INVAL E_DUP_ENDPOINT REFRESH_TURN_PORT_ERROR ALLOC_TURN_PERMISSION_BINDING_ERROR FREE_TURN_PERMISSION_BINDING_ABORTED KEEP_UDP_HOLE_PUNCHING_ERROR retry_list use_static_session enable_happy_eyeballs wait_game_result_timeout_sec IDELAY_OVER_KEEP_BUF_SIZE_COUNT_MAX CONGESTION_CONTROL_WINDOW_SIZE_LIMIT_ MATCH_STOP_COUNT_BUF

OFFSET=0xad82d4 TERM=relay
CONTEXT=DE IMPL : %s call(%d)[%d] level = %d UE FADE IMPL : %s call(%d)[%d] Level = %d. Now State = %d CheckValid /Game/Assets/ui/Data/Widget/Mode/eFWorld/ModeMainMenuMatch/ModeMainMenuMatch.ModeMainMenuMatch_C Online/EvCompe/MenuEvCompeLocalGamerelay Online/EvCompe/EventCompe/MenuEvCompeEventCompeCompeCampaignRankingTypeAssist Online/EvCompe/MlEvent/Management/Contract/MenuMlEventContractMyteamPlayerDetail Online/EvCompe/MlEvent/Management/Contract/MenuMlEventContractMyteamCoachList Online/EvCompe/MlEvent/Management/Contract/MenuMlEventContractStandardCoachDetail GamePlan/CoachLinkList Match/Sugoroku/Su

OFFSET=0xb53a2c TERM=relay
CONTEXT=wrong file format?) connection is not setup for websocket curl_ws_send(len=%zu, fragsize=%ld, flags=%x, raw=%d) -> %d, %zu bodies airResistanceRate matchPlanDataSync L_mic_2L R_mic_2L abilityExplosePowerAdd dragSpeedMin frictionRollRateMax relayBallPosZ goalKickMode distMin airBattle tackle kind0 p1_length_max frame_min gageTest autoRecieveSpeedDecDistMin accRateDif120 controlShootGageMid99 adjustPassGetSpeedFly moveContinueFrameAdjustZposi checkSectorDist blendStartAfterFrame speed_28 reactionTime reactionIK reactionOwnBall AwaySeatDirection adjustDiv backOffsideLine dfLineBack forceDashDistDefenc

OFFSET=0xb553c7 TERM=relay
CONTEXT=ct_num is_need_refund_reversed_detect_notice league_division_info mute_list_actual_max home_player_list base_value recruit_challenge_not_received_num COIN CmdSendAnalysisLog.php is_already_reported title_label create_session_time CmdSetGamerelayQuality.php CmdSetLanguage.php playstyle_com emoji_frame_home_info strike_arena_gameplayer default_member CMD_SET_EVENT_LEAVE CmdSkipEventMatch.php team_data_lists is_need_default_member formation_str squad_log CMD_GET_ML_EVENT_EPISODE_HISTORY fans_increase_info CmdGetMlEventMarketFreePlayerlist.php narrow_down_type search_info CmdSendMlEventEpisodeChoicesIn

OFFSET=0xba11b8 TERM=relay
CONTEXT=R EARLY_STAGE TUTORIAL_OBJECT_KIND_DUMMY_RACK_X4 cpk_dat/common/match/path_to_glory_replay/path_to_glory_replay_11.trep cpk_dat/common/match/tutorial_replay/tutorial_replay_matchup_04.trep ChatSystem proceed_squad_challenge EvCompeLocalGamerelay MlEventReleasePlayerList Sim/Match/SimMatchSetting Online/Quick/QuickMain Mode/CommandErrorTest/CommandErrorTestMain AssetShopList SE_CARDPACK_SKIP_02 CmdGetMyclubStandardDraftList CmdSetMyclubMainSquad Review IsNeedMyClubTeamEntry testDirectMenu SeasonPointRentalPlayerList CloseAgeInput ClearSelect BundledProductName TotalPaidVal CmdBuyExchange ExchangeIte

OFFSET=0xba18aa TERM=relay
CONTEXT=ION PLAY_ANY_MATCH_WITH_SPECIAL_BINGO COLLABO_KIND_01 FLUCTUATE_STAMINA ERR_LOGIN_FAILED ERR_NOT_REGISTERED ERR_INVALID_RECRUIT_CODE card_gameplayer_id OffenseInstructions _0x expiringFeeeCoins country_name CmdGetGameTeamList.php CmdGetGamerelayQualitycheckList.php CmdGetIsParentalPermission.php coin_banner_file_name event_guide_alert_info is_timer_alert league_phase_start_time league_phase_end_time promotion_id detail_str ITEM CMD_SET_GAME_RESULT balance playstyle promotion_id_list first_match_player_list PRESET_CHALLENGE data_category event_num CMD_GET_EVENT_RANKING_LOG self_record_data_lists is_

OFFSET=0xbb60f6 TERM=relay
CONTEXT=r_file_name ONLINE_COMPE notification_url communication_antenna_status_info CmdGetUserAgeKind.php setplay_ck_right profile_banner CMD_SET_PROMOTION_READ CmdSetSeasonUpdateInfo.php emoji_frame_away_info CmdUpdateTermsToService.php build_gamerelay_num achievement_type CmdCreateMlEventSquad.php ml_event_team CMD_GET_FRIEND_LIST CMD_GET_LEAGUE_INFO CMD_CREATEJOIN_ROOM campaign_pass_banner void_player_ticket_info CMD_GET_MYCLUB_ENTRY_INFO CmdGetMyclubWarehousePlayerlist.php CmdSetMyclubCustomStadium.php is_update_first_time_levelup BUY_BY_GP BUY_BY_TICKET ability_Id voting_start_date CMD_GET_SEASON_RECO

OFFSET=0xbee509 TERM=relay
CONTEXT=ex AgeSegDesc TotalPaidKey MLEvent_1 FrameState.TeamSelect.Menu.StepHA isFadeEnd onlineinterruption::PRIORITY_3 onlinemode::AssetPackStartProcTask CmdGetAvatarInfoList CmdEntryUserCompe CmdSetMlEventSquadInfo CmdSetRoomMatchReady CmdGetGamerelayQualityCheckList CmdSetGameResult CmdSetPathtogloryGameResult target_user_id_list user_id panel_mission_id reason_num pattern duplicate_avatar_set_type nsa_id player_rate_list available_time_max defense_sub_com_level bg_file_name viewing_id is_unlimited reward_info_list match_entry disp_max_overall is_com condition_team_power auto_attack_level team_power con

OFFSET=0x2c7472 TERM=Candidate
CONTEXT=naStreamer_ExecuteStreaming criManaStreamer_GetBps criManaStreamer_GetBufferMaxSize criManaStreamer_GetBufferRemainSize criManaStreamer_GetEmergencyThresholdTime criManaStreamer_GetMinimumReadSize criManaStreamer_IsActive criManaStreamer_IsCandidate criManaStreamer_IsClosing criManaStreamer_IsOpened criManaStreamer_IsStreaming criStreamerManager_AddStreamerByDeviceId criStreamerManager_CalculateWorkSizeForLibrary criStreamerManager_DeleteStreamerByDeviceId criStreamerManager_Execute criStreamerManager_Finalize criStreamerManager_GetEmergencyThresholdTime criStreamerManager_Initialize criStreamerManager

OFFSET=0x9d1ecc TERM=Candidate
CONTEXT=on::WaitingForLocation EARWorldAlignment bRenderMeshDataInWireframe EARDepthAccuracy::Accurate EARTextureType::PersonSegmentationImage TrackedPose EARLineTraceChannels::PlaneUsingExtent EARCaptureType::Camera ImageResolution GetBoundingBox CandidateObjectData GetOrientationAndPosition UpdateExternalTrackingHMDPosition SystemId EXRTrackedDeviceType GripRotation EnableMotionTrackingOfDevice AxisGesture LPVDirectionalOcclusionRadius UseMask RandomPitchAngle MaxInitialAge TouchingActorEntryPosition ProceduralGuid Grass G:/UE4.26_eFB/Base/Engine/Source/Runtime/Engine/Classes/Materials/MaterialInterface.h Br

OFFSET=0x9f8d7c TERM=Candidate
CONTEXT=elocity1 Mass2 SurfaceType13 SurfaceType17 DefaultGravityZ BounceThresholdVelocity SolverOptions StartReconstruction EMeshTrackerVertexColorMode::Block GetPointCloud PinComponentToARPin SaveARPinToLocalStore StartARSession TextureType ARGetCandidateObjectPin__DelegateSignature AltitudeMeters CheckARServiceAvailability GetARDependencyHandler EAREnvironmentCaptureProbeType::None CandidateObject TraceChannel EARFaceTrackingDirection::FaceRelative GetExtent EARCandidateImageOrientation EARAltitudeSource::Unknown EARObjectClassification::NotApplicable EARTrackingQualityReason::ExcessiveMotion EARLineTraceCh

OFFSET=0x9f8e08 TERM=Candidate
CONTEXT=Mode::Block GetPointCloud PinComponentToARPin SaveARPinToLocalStore StartARSession TextureType ARGetCandidateObjectPin__DelegateSignature AltitudeMeters CheckARServiceAvailability GetARDependencyHandler EAREnvironmentCaptureProbeType::None CandidateObject TraceChannel EARFaceTrackingDirection::FaceRelative GetExtent EARCandidateImageOrientation EARAltitudeSource::Unknown EARObjectClassification::NotApplicable EARTrackingQualityReason::ExcessiveMotion EARLineTraceChannels::PlaneUsingBoundaryPolygon FocalLength /Script/AugmentedReality GetTrackingToWorldTransform TextureRectMin EHandKeypoint::IndexProxim

OFFSET=0x9f8e59 TERM=Candidate
CONTEXT=n TextureType ARGetCandidateObjectPin__DelegateSignature AltitudeMeters CheckARServiceAvailability GetARDependencyHandler EAREnvironmentCaptureProbeType::None CandidateObject TraceChannel EARFaceTrackingDirection::FaceRelative GetExtent EARCandidateImageOrientation EARAltitudeSource::Unknown EARObjectClassification::NotApplicable EARTrackingQualityReason::ExcessiveMotion EARLineTraceChannels::PlaneUsingBoundaryPolygon FocalLength /Script/AugmentedReality GetTrackingToWorldTransform TextureRectMin EHandKeypoint::IndexProximal EHandKeypoint::MiddleDistal EXRDeviceConnectionResult XRGestureConfig bOverrid

OFFSET=0xa30bf9 TERM=Candidate
CONTEXT=oad Extents InstallARService EARFaceTrackingUpdate EAREnvironmentCaptureProbeType::Manual EARPlaneDetectionMode::None SetSceneReconstructionMethod EARDepthAccuracy::Unkown EARFaceBlendShape::EyeLookDownRight GetCenter ARCameraIntrinsics GetCandidateObjectData GetWorldToMetersScale SetWorldToMetersScale SetAssociatedPlayerIndex PostInitViews_FlushDel RenderTranslucency MeshBounds bReceivesDecals ReapplyGroundSlope RuntimeVirtualTextures Clear_Heightmap DebugChannelR LGT_Weight EGrassScaling::LockXY CollisionQuadFlags EndSideFalloff StartRoll InRenderTarget InExportHeightIntoRGChannel LandscapeMaterialsO

OFFSET=0xa43998 TERM=Candidate
CONTEXT=RObjectUpdatePayload EARGeoTrackingAccuracy SpawnedActor LocalToAlignedTrackingTransform EARLightEstimationMode GetFaceTrackingDirection ShouldEnableCameraTracking bGenerateMeshDataFromTrackedGeometry bUseSceneDepthForOcclusion SerializedARCandidateImageDatabase ObjectComponentClass GetARSharedWorldGameState EARTextureType::CameraImage EAREye::LeftEye EARFaceBlendShape::EyeLookUpLeft EARCaptureType::QRCode GestureConfig bClearBlack InDisconnectedDelegate EHandKeypoint::IndexMetacarpal EHandKeypoint::MiddleTip EXRDeviceConnectionResult::FeatureNotSupported EHMDWornState::Type HMDTrackingInitializedDeleg

OFFSET=0xa6a18a TERM=Candidate
CONTEXT= ComponentToPin PinToRemove EPlaneComponentDebugMode::ShowNetworkRole EARServicePermissionRequestResult::Denied EARGeoTrackingState::Localizing AmbientColorTemperatureKelvin OnARTransformUpdated EARFrameSyncMode::SyncTickWithCameraImage AddCandidateImage GetEnabledSessionTrackingFeature GetLightEstimationMode EARTextureType::SceneDepthMap EARFaceBlendShape::EyeWideLeft EARFaceBlendShape::MouthFunnel EARFaceBlendShape::MouthStretchLeft BoundaryPolygon BlendShapes_Key GetTrackedPoseData OnRemoveTrackedGeometry OnUpdateTrackedPoint OnRemoveTrackedFace OnRemoveTrackedEnvProbe EARJointTransformSpace::Parent

OFFSET=0xaa3219 TERM=Candidate
CONTEXT=itScreenType::Horizontal StatusFlags Field_RadialVectorFalloff EGeometryCollectionPhysicsTypeEnum::Chaos_LinearVelocity FilterEnabled CTF_MAX ESleepFamily::Custom SurfaceType10 /Script/MRMesh InMaterial bUpdateNavMeshOnMeshUpdate AddRuntimeCandidateImage LoadARPinsFromLocalStore PinComponentToTraceResult ResizeXRCamera SessionConfig EGeoAnchorComponentDebugMode::ShowGeoData EImageComponentDebugMode DetectedImage ARPlaneUpdatePayload TransformSetting EARServiceInstallRequestResult ServerSpawnARActor GetAmbientColorTemperatureKelvin DebugDraw EARSessionTrackingFeature::PoseDetection2D EARFaceTrackingUpda

OFFSET=0xaa33db TERM=Candidate
CONTEXT=ing EARServiceInstallRequestResult ServerSpawnARActor GetAmbientColorTemperatureKelvin DebugDraw EARSessionTrackingFeature::PoseDetection2D EARFaceTrackingUpdate::CurvesAndGeo NewFormat ImageComponentClass EARFaceBlendShape::MouthPucker EARCandidateImageOrientation::Portrait EARObjectClassification::Face EARTrackingState::Tracking ARSkeletonDefinition IsDeviceTracking IsInLowPersistenceMode SetXRDisconnectDelegate HMDData NewScale EHandKeypoint::LittleTip ESpectatorScreenMode::Disabled EHMDTrackingOrigin::Unbounded GripPosition IsMotionTrackingEnabledForSource HMDConnectCanceledDelegate UpdateGPUScene 

OFFSET=0xab6a74 TERM=Candidate
CONTEXT=dShape::MouthLowerDownLeft EARFaceBlendShape::RightEyeYaw EARFaceTrackingDirection IsTracked GetBoundaryPolygonInLocalSpace EnvironmentCaptureTexture TrackedEnvProbe OnUpdateTrackedImage OnAddTrackedFace OnUpdateTrackedEnvProbe ARPose2D GetCandidateTexture bDrawEyeFirst EHandKeypoint::MiddleIntermediate EXRTrackedDeviceType::TrackingReference EXRTrackedDeviceType::Any ESpectatorScreenMode::Texture EXRSystemFlags::IsTablet DisplayMeshMaterialOverrides ESpatialInputGestureAxis::NavigationRails DeltaRotation DeferredShadingSceneRenderer_DBuffer AfterBasePass RenderForwardShadingShadowProjections LPVVplInj

OFFSET=0xadc379 TERM=Candidate
CONTEXT=orm TraceResult EARFaceTransformMixing EARServiceInstallRequestResult::UserDeclinedInstallation EARServiceInstallRequestResult::FatalError EARServiceAvailability::UnknownChecking EARSceneReconstruction EARLightEstimationMode::None InUpdate CandidateImages DesiredVideoFormat SetPreviewImageData PreviewImageData bIsTemporallySmoothed EAREye EARFaceBlendShape::MouthLowerDownRight EARFaceBlendShape::MouthUpperUpLeft EARFaceBlendShape::MouthUpperUpRight EARFaceBlendShape::BrowInnerUp EARFaceBlendShape::CheekSquintRight UnderlyingMesh TrackedPoint OnAddTrackedPoint EARSessionStatus::NotSupported EARTrackingQ

OFFSET=0xaef846 TERM=Candidate
CONTEXT=DebugMode DefaultMeshMaterial GetMRMesh SetNativeID SetImageComponentDebugMode EARServiceAvailability EARGeoTrackingState OptionalAnchorName OnARTrackingStateChanged EARPlaneDetectionMode::HorizontalPlaneDetection SetResetCameraTracking NewCandidateImage bUseMeshDataForOcclusion EnabledSessionTrackingFeature PointComponentClass SetARSharedWorldData EARTextureType::Unknown EAREye::RightEye EARFaceBlendShape::EyeBlinkRight GetUnderlyingMesh EARWorldMappingState::Mapped EARSessionStatus::Running EARSessionStatus::FatalError EARTrackingQualityReason::Initializing EARCaptureType EARTrackingState::StoppedTra

OFFSET=0xb15854 TERM=Candidate
CONTEXT=sion bMaintainUpDirection EPlaneComponentDebugMode::ShowClassification MyTrackedGeometry Payload EARServiceAvailability::UnknownError EARGeoTrackingStateReason::NeedLocationPermissions EARSessionType::Face GetEnvironmentCaptureProbeType SetCandidateObjectList FrameSyncMode bEnableAutomaticCameraOverlay CaptureProbe EARTextureType EARFaceBlendShape::MouthDimpleRight EARFaceBlendShape::HeadPitch UniqueId OnAddTrackedObject EARWorldMappingState::NotAvailable EARSessionStatus::PermissionNotGranted JointLocations GetXRSystemFlags IsSpectatorScreenModeControllable HMDReconnectedDelegate VRControllerRecentere

OFFSET=0xb73d4f TERM=Candidate
CONTEXT=pdateVertexNormal bFaceOutOfScreen bIsAvailable GetAmbientColor EARSessionTrackingFeature::SceneDepth EARSessionType::Image bEnableAutomaticCameraTracking bResetCameraTracking EARFaceBlendShape::MouthFrownLeft EARFaceBlendShape::HeadYaw EARCandidateImageOrientation::Landscape EARTrackingQuality::NotTracking EnableHMD GetHMDWornState SetClippingPlanes bProvidedAngularVelocity TrackingStatus bDisableLowLatencyUpdate bDisplayDeviceModel bNavigationAxisY RenderCustomDepthPass LPVSize MapCheck /Script/Foliage FOLIAGEVERTEXCOLORMASK_Green VertexColorMaskByChannel bCastStaticShadow FoliageDamping ESimulationQ

OFFSET=0xb8782e TERM=Candidate
CONTEXT=ectClassificationAtLocation MaxLocationDiff SessionType EARFaceTransformMixing::ComponentLocationTrackedRotation SessionPayload AltitudeSource OutAvailability EARGeoTrackingState::NotAvailable GetGeoTrackingAccuracy SetDesiredVideoFormat InCandidateObjects bGenerateCollisionForMeshData bUsePersonSegmentationForOcclusion WorldAlignment CandidateObjects ClientUpdatePreviewImageData InCaptureProbe EARDepthQuality::High EARFaceBlendShape::JawLeft Orientation TrackableObjectDelegate__DelegateSignature TrackedImage EARObjectClassification::HandMesh EARPlaneOrientation::Diagonal EARTrackingQualityReason::Insu

OFFSET=0xb8788f TERM=Candidate
CONTEXT=TrackedRotation SessionPayload AltitudeSource OutAvailability EARGeoTrackingState::NotAvailable GetGeoTrackingAccuracy SetDesiredVideoFormat InCandidateObjects bGenerateCollisionForMeshData bUsePersonSegmentationForOcclusion WorldAlignment CandidateObjects ClientUpdatePreviewImageData InCaptureProbe EARDepthQuality::High EARFaceBlendShape::JawLeft Orientation TrackableObjectDelegate__DelegateSignature TrackedImage EARObjectClassification::HandMesh EARPlaneOrientation::Diagonal EARTrackingQualityReason::InsufficientLight EARTrackingQualityReason SetCandidateObjectData InCandidateObject ClearXRTimedInput

OFFSET=0xb879c9 TERM=Candidate
CONTEXT=ty::High EARFaceBlendShape::JawLeft Orientation TrackableObjectDelegate__DelegateSignature TrackedImage EARObjectClassification::HandMesh EARPlaneOrientation::Diagonal EARTrackingQualityReason::InsufficientLight EARTrackingQualityReason SetCandidateObjectData InCandidateObject ClearXRTimedInputActionDelegate GetNumOfTrackingSensors BottomFOV EHandKeypoint::IndexIntermediate EHandKeypoint EXRSystemFlags EHMDWornState::NotWorn EHMDTrackingOrigin::Floor HandKeyRadii bOverride_LPVSecondaryOcclusionIntensity LPVIntensity ScaleY RandomYaw bUseAsOccluder MaxInitialSeedOffset OtherComp WeightmapTextureChannel 

OFFSET=0xb879df TERM=Candidate
CONTEXT=hape::JawLeft Orientation TrackableObjectDelegate__DelegateSignature TrackedImage EARObjectClassification::HandMesh EARPlaneOrientation::Diagonal EARTrackingQualityReason::InsufficientLight EARTrackingQualityReason SetCandidateObjectData InCandidateObject ClearXRTimedInputActionDelegate GetNumOfTrackingSensors BottomFOV EHandKeypoint::IndexIntermediate EHandKeypoint EXRSystemFlags EHMDWornState::NotWorn EHMDTrackingOrigin::Floor HandKeyRadii bOverride_LPVSecondaryOcclusionIntensity LPVIntensity ScaleY RandomYaw bUseAsOccluder MaxInitialSeedOffset OtherComp WeightmapTextureChannel ToolMaterial MaterialI

OFFSET=0xbae296 TERM=Candidate
CONTEXT=Enum::Chaos_Implicit_LevelSet EImplicitTypeEnum ECollisionTypeEnum EChaosThreadingMode::DedicatedThread AngularVelocity cleaning the mesh failed EBodyCollisionResponse::Type ForceNavMeshUpdate TrackedGeometryGroup RemoveARPinFromLocalStore CandidateTexture bDeletePointsWithSameName StartPoints bTestPlaneBoundaryPolygon Pin EPlaneComponentDebugMode::None EARSessionConfigFlags::GenerateMeshData ARPoseUpdatePayload EARLightEstimationMode::AmbientLightEstimate GetCandidateObjectList bHorizontalPlaneDetection MaxNumberOfTrackedFaces SetARWorldSharingIsReady ARWorldData PreviewImageSize SetEnvironmentCapture

OFFSET=0xbae376 TERM=Candidate
CONTEXT=nFromLocalStore CandidateTexture bDeletePointsWithSameName StartPoints bTestPlaneBoundaryPolygon Pin EPlaneComponentDebugMode::None EARSessionConfigFlags::GenerateMeshData ARPoseUpdatePayload EARLightEstimationMode::AmbientLightEstimate GetCandidateObjectList bHorizontalPlaneDetection MaxNumberOfTrackedFaces SetARWorldSharingIsReady ARWorldData PreviewImageSize SetEnvironmentCaptureProbe ExternalTextureGuid EARFaceBlendShape::EyeLookOutRight EARFaceBlendShape::MouthSmileLeft EARFaceBlendShape::TongueOut GetLastUpdateTimestamp GetAltitudeSource OnRemoveTrackedPoint EARAltitudeSource EARObjectClassificat

OFFSET=0xbc1bfc TERM=Candidate
CONTEXT=EARGeoTrackingStateReason::GeoDataNotLoaded CheckGeoTrackingAvailabilityAtLocation AmbientColor PinnedComponent EAREnvironmentCaptureProbeType::Automatic EARSessionType::ObjectScanning EARSessionType EARWorldAlignment::GravityAndHeading AddCandidateObject K2_OnARWorldMapIsReady EARTextureType::CameraDepth EARTextureType::PersonSegmentationDepth EARFaceBlendShape::MouthSmileRight EARFaceBlendShape::MouthShrugUpper OnAddTrackedPlane OnRemoveTrackedPlane OnRemoveTrackedObject WorldContext Hand EyeRectMax ESpectatorScreenMode::Distorted DisableMotionTrackingOfSource EnableMotionTrackingForComponent VRNotif

OFFSET=0xbe7762 TERM=Candidate
CONTEXT=nstruction ScanWorld SavedObject EPlaneComponentDebugMode OnRep_Payload ServerUpdatePayload NewDebugMode SetQRCodeComponentDebugMode EARGeoTrackingStateReason::None EARSessionTrackingFeature EARPlaneDetectionMode::VerticalPlaneDetection GetCandidateImageList GetSceneReconstructionMethod SetFaceTrackingDirection ShouldRenderCameraOverlay bGenerateNavMeshForMeshData bTrackSceneObjects EARFaceBlendShape::MouthRollLower EARJointTransformSpace::Model EARJointTransformSpace PrincipalPoint ConfigureGestures GetDevicePose MotionControllerData TopFOV Far EXRVisualType::Controller EHandKeypoint::IndexDistal EHan

OFFSET=0xc0d9d7 TERM=Candidate
CONTEXT=onType AccumulatedImpulse EBodyCollisionResponse::BodyCollision_Enabled CTF_UseSimpleAndComplex ELinearConstraintMotion EAngularConstraintMotion AngularEtherDrag EFrictionCombineMode::Min IsSceneReconstructionSupported SetARWorldScale ARGetCandidateObject EPoseComponentDebugMode::None JointTransforms EARSessionTrackingFeature::PersonSegmentation EARFaceTrackingUpdate::CurvesOnly bNewValue bEnableAutoFocus bResetTrackedObjects BufferSizePerChunk PreviewImageBytesDelivered EARFaceBlendShape::EyeLookOutLeft EARFaceBlendShape::JawForward GetBlendShapeValue TrackedPlane OldToNewTransform EARObjectClassifica

OFFSET=0x24d811 TERM=candidate
CONTEXT=TSN6icu_6420LanguageBreakFactoryE _ZTSN6icu_6423ICULanguageBreakFactoryE _ZTVN6icu_6415UnhandledEngineE _ZTVN6icu_6419LanguageBreakEngineE _ZTVN6icu_6420LanguageBreakFactoryE _ZTVN6icu_6423ICULanguageBreakFactoryE _ZN6icu_6412PossibleWord10candidatesEP5UTextPNS_17DictionaryMatcherEi _ZN6icu_6412PossibleWord12acceptMarkedEP5UText _ZN6icu_6412PossibleWord6backUpEP5UText _ZN6icu_6414CjkBreakEngineC1EPNS_17DictionaryMatcherENS_12LanguageTypeER10UErrorCode _ZN6icu_6414CjkBreakEngineC2EPNS_17DictionaryMatcherENS_12LanguageTypeER10UErrorCode _ZN6icu_6414CjkBreakEngineD0Ev _ZN6icu_6414CjkBreakEngineD1Ev _ZN6ic

OFFSET=0xa4a903 TERM=candidate
CONTEXT=m extra_entity_id go_match_users lost_goal_num first_place_info event_reward_list is_current_mission is_ranking_fix top_scorer_myclub_gameplayer is_available eula_url pt_ranking_start_point esports_end_str_body has_campaign es_is_authentic candidate_max candidate_min DATA_PARAMETER_R_FOOT_FREQUENCY DATA_PARAMETER_S_QUICK_TOUCH DATA_PARAMETER_S_INTERCEPT DATA_PARAMETER_S_AIR_BATTLE DATA_PARAMETER_S_GK_RUSH_OUT DATA_PARAMETER_ABILITY3 PLAY_STYLE_ADVANCED_GK SKILL_CARD_PIVOT_FOOT_TOUCH SKILL_CARD_LONG_RANGE_DRIVE SKILL_CARD_QUICK_IMPACT SKILL_CARD_THROUGH_PASS SKILL_CARD_PIN_POINT_CROSS SKILL_CARD_LOW_LOB

OFFSET=0xa4a911 TERM=candidate
CONTEXT=_id go_match_users lost_goal_num first_place_info event_reward_list is_current_mission is_ranking_fix top_scorer_myclub_gameplayer is_available eula_url pt_ranking_start_point esports_end_str_body has_campaign es_is_authentic candidate_max candidate_min DATA_PARAMETER_R_FOOT_FREQUENCY DATA_PARAMETER_S_QUICK_TOUCH DATA_PARAMETER_S_INTERCEPT DATA_PARAMETER_S_AIR_BATTLE DATA_PARAMETER_S_GK_RUSH_OUT DATA_PARAMETER_ABILITY3 PLAY_STYLE_ADVANCED_GK SKILL_CARD_PIVOT_FOOT_TOUCH SKILL_CARD_LONG_RANGE_DRIVE SKILL_CARD_QUICK_IMPACT SKILL_CARD_THROUGH_PASS SKILL_CARD_PIN_POINT_CROSS SKILL_CARD_LOW_LOB ABILITY_COLLA

OFFSET=0xb8d229 TERM=candidate
CONTEXT=file Malformed option provided in a setopt RTSP CSeq mismatch or invalid CSeq An authentication function returned an error Malformed input to a URL function Bad user Connection died, retrying a fresh connect (retry count: %d) Found pending candidate for reuse and CURLOPT_PIPEWAIT is set %s%s.netrc Error %d sending MQTT CONNECT request %u.%u.%u.%u 0123456789abcdefABCDEF:. public key hash: sha256//%s issuer: %s Next protocol Issuer %02x SSL: unable to obtain common name from peer certificate SSL_ERROR_WANT_X509_LOOKUP curl_ws_recv(len=%zu) -> %zu bytes (frame at %ld, %ld left) ListenerWorkerPES %u pes:

OFFSET=0x9e19ce TERM=HalfTime
CONTEXT=e StartCapture GoalNetIndexSimToData GetRandomAssetIDsTest ScarfDMI EAdFormat::Banner160x600 EAdFormat::Banner970x250 ScrollIndex ChildLevels LevelSetTableRow SetShouldBeVisible bShouldBeLoaded GetTeamColors EMatchFlow::InPlay EMatchPhase::HalfTime EMatchPhase::ExInterval TargetType InTargetType ReplaceMovieFileStr GetLoadMapRequest FinishGameModeCheckEventDispatcher__DelegateSignature isLoginSuccess FinishOnlineLogin isFlowMenu m_maintenanceStrHeadline ESupporterShirtType UnloadLightLevel SpotLights bIsLightLoadMode AddPlayer Light InitLattice SetFacialBoneOffsetMap SolidFacialhairs GetMontageBaker R

OFFSET=0x9e36c3 TERM=HalfTime
CONTEXT=dLCameraButton OnPressedFrameByFrameMinusButton GetStrLoadingText EMenuMatchKickerSelectKickerStateType::ABILITY m_positionStr m_setupMenuData m_isEvaluationMom IsPKorAggregateScore NeedUpdateHighlightIcon GetLocalSkinType IsFirstPkMatch IsHalfTime StartLoadCustomStadiumTexture ex timeKind EMenuMatchSettingsMatchTime::MATCH_TIME_1 EMenuMatchSettingsMatchTime::MATCH_TIME_30 isRaderPosSide SendEndTexture isExtraUni RewardIconType isPresent GetAchievementRecvList IsWelcomeAlertNeeded IsInvite GetCoachNumStr m_name m_isInactive m_isRightArrowActive IsGrowUpParameter IsTopCareerPlanDisp TrainingLevelItem E

OFFSET=0xa125ca TERM=HalfTime
CONTEXT=T_KIND_START_AREA_POINT cpk_dat/common/match/tutorial_replay/tutorial_replay_shooting_02.trep MenuAlertImageDialog NotificationManager 00 CmdSetNewslist m_pTaskSyncPlayerData is null QRViewKidPage cpk_dat/test/tex/Sponsor_ MatchPause Match/HalfTime/MatchHalfTimePost CmdGetExhibitionESportsInfo MenuCampaignPassCollectionAfterMenu CmdRecvMyclubAchievement MyClubAchivementBingoList CmdBuyMlEventLife SE_PLAYER_PROGRESSED MyClubPackAnnounceView CanDispInheritPlayerListAlert CmdDeleteMyclubSquad CmdGetPathtogloryInfo TransactionNoticeView QMyClubTestFloat CancelAlertBody SelectedTeamId MenuFadeTestView CmdG

OFFSET=0xa125d8 TERM=HalfTime
CONTEXT=REA_POINT cpk_dat/common/match/tutorial_replay/tutorial_replay_shooting_02.trep MenuAlertImageDialog NotificationManager 00 CmdSetNewslist m_pTaskSyncPlayerData is null QRViewKidPage cpk_dat/test/tex/Sponsor_ MatchPause Match/HalfTime/MatchHalfTimePost CmdGetExhibitionESportsInfo MenuCampaignPassCollectionAfterMenu CmdRecvMyclubAchievement MyClubAchivementBingoList CmdBuyMlEventLife SE_PLAYER_PROGRESSED MyClubPackAnnounceView CanDispInheritPlayerListAlert CmdDeleteMyclubSquad CmdGetPathtogloryInfo TransactionNoticeView QMyClubTestFloat CancelAlertBody SelectedTeamId MenuFadeTestView CmdGetSeasonSchedu

OFFSET=0xa8418e TERM=HalfTime
CONTEXT=passing_01.rep cpk_dat/common/match/tutorial_replay/tutorial_replay_through_pass_04.trep FameDetailView General Mode/MenuSystem/PopChildWithInterruption/ListPopChildWithInterruption EulaAgree EvCompeAnnounceViewCompe MailboxBase MatchResultHalfTime MatchSugorokuPlayerList MenuMyClubAchievementTypeDownloader CmdUseMyclubStandardDraft ChangeSquadListAlertTitle CompletePurchase EditNGAlertNameButton SettingsVisualQuality cpk_dat/common/credit/credit.bin SettingsSupport PrepareData CancelAge SystemAlertType HistoryCol5 SpecialPlayer_3 AILeague_1 data_list CmdSuccessAdvertisement CmdGetUserCompeObserveMatc

OFFSET=0xac504a TERM=HalfTime
CONTEXT=inMenu /Game/Assets/ui/Data/Widget/Mode/Event/CompeCampaignRank/CompeCampaignRank.CompeCampaignRank_C /Game/Assets/ui/Data/Widget/Mode/Event/MatchMenuTournament/MatchMenuTournament.MatchMenuTournament_C Match/Result/MatchResultCoopStatsFromHalfTime Online/Lobby/StrikeArena/MenuStrikeArenaPlayerSelect Match/Result/MenuMatchResultUserList Online/UserCompe/MenuUserCompeEntryLobby MyClub/MyTeam/PlayerSkillTraining MyClub/Contract/AgentList MyClub/Contract/PlayerDetailMobile Online/Season/MenuSeasonPointMenu Settings/Help/MenuSettingsTipsDetail Settings/UserInfo/MenuSettingsUserPersonalInfo Settings/LegalP

OFFSET=0xbee231 TERM=HalfTime
CONTEXT=ONE TOTAL MATCH_LEVEL_AMATEUR PATH_TO_GLORY_OBJECT_KIND_START_AREA_POINT cpk_dat/common/match/path_to_glory_replay/path_to_glory_replay_01_02.trep MenuAlertRewardSelection Over the word count MannerWarningDialog MlEventFreePlayerList Match/HalfTime/MatchHalfTime MyClub/Contract/AgentDemoBanner Online/Match/MatchProcessMatchSettingsInit MenuCampaignPassCollectionMissionMenu MyClubExchangePlayerTicketList CmdGetMyclubScoutPlayerList SE_DIALOG_MISSION_COMPLETE MyClubMyTeamPlayerTrainingBooster MyClubMyTeamPlayerTrainingSkillCategory ShopCoin IsMyClubNeedEntryByLicenseOut EditAlertEditTeamNameShort EditEm

OFFSET=0xbee23f TERM=HalfTime
CONTEXT=H_LEVEL_AMATEUR PATH_TO_GLORY_OBJECT_KIND_START_AREA_POINT cpk_dat/common/match/path_to_glory_replay/path_to_glory_replay_01_02.trep MenuAlertRewardSelection Over the word count MannerWarningDialog MlEventFreePlayerList Match/HalfTime/MatchHalfTime MyClub/Contract/AgentDemoBanner Online/Match/MatchProcessMatchSettingsInit MenuCampaignPassCollectionMissionMenu MyClubExchangePlayerTicketList CmdGetMyclubScoutPlayerList SE_DIALOG_MISSION_COMPLETE MyClubMyTeamPlayerTrainingBooster MyClubMyTeamPlayerTrainingSkillCategory ShopCoin IsMyClubNeedEntryByLicenseOut EditAlertEditTeamNameShort EditEmptyAlertShortB

OFFSET=0x9baf95 TERM=Halftime
CONTEXT=TargetChanged bIsBackGround GetAudienceFlagClipBit GetCameraTarget SetGoalDemoMode SetPkMatchKickerSide SetTimeDir OnEnterGoalEvent EMatchFlowTask::FadeOutWipe EMatchFlowTask::ReplayHighlight EMatchFlowTask::ReplayOutofplay EMatchFlowTask::HalftimeMenu EMatchEffectType::PowerDribble_Aura EMatchEffectType::PowerDribble_Armor GoalPlayer GoalInfo To FilterByRegex GetWorkSelectTeamId GetCommandMax SetupToolTip CallbackConfirmRecommendedAlertCancel ModelViewAnime EnableHairStrands GetResolution SetBodyAnime AnimeTableRow RemoveCoach Nose EarWidth m_skeletalMesh UniqueParams GetEnableAutoSave HairEndsColorR

OFFSET=0xafe958 TERM=Halftime
CONTEXT=tor m_pMaterialNetCustom CommandList reason MatchFlowChanged SetGameState OnEndMatchDelegate__DelegateSignature MatchEventObservers EMatchFlowTask::DemoTimeupTrans EMatchFlowTask::FadeInBlack EMatchFlowTask::ForcedFormation EMatchFlowTask::HalftimeEnd EMatchEffectType::Efbx05_Armor EMatchEffectType::Efbx07_Aura EMatchEffectType::Efbx10_Armor EndEventTimer GetScoreAt EMenuSysLogType SourceAssets SetIsReady UpdateOnlineLogin bEnableLoginPlugin m_isForceCancelCommandErrorDialog MenuWindow UpdateRenderTargetSize ComponentTransform GetEyelidNormalTexture map points transforms_Key ComponentHair MeshEye Tran

OFFSET=0x9dcd45 TERM=HALFTIME
CONTEXT=OT_LOW ATTACK DIFENCE HALF BOX_TO_BOX INCISIVE_RUN A1_LP_PGK A1_LP_PP2 A1_LP_PPC A1_TEAM6 CHANT_CALL_GOAL SOUNDSYS_CHEER Def_Sound_Sys_Preset_Volume_TV_Commentary DspBusSetting_01 SE_Mode_AM BGM_Match_AM SA_SYNTH_ PreInstall SE_ENTER_AFTER_HALFTIME Rain KSVOCINF all.str sys_kor_diff.str EnableMasterFlag (Landroid/content/Context;I)V dt261 _mobile_all.cpk Fail Deleting:%d (%s), AssetPack::UpdateDelete AssetPackCheck : %d AssetPack Judge ReDownload [%s] ASSET_PACK_UNKNOWN subscribeToTopic cancelAll 110001100011000 011101000000110 010010010110100 jpn ___Z Ua9enable_ifI non-virtual thu

OFFSET=0xa4a455 TERM=HALFTIME
CONTEXT=_OUT ANIME_DEMO_OUTOFPLAY ANIME_LINESMAN FEINT_KIND_KICK_NUTMEG_L FEINT_KIND_DRAWOPENCLOSE_L FEINT_KIND_NUTMEG_RIQUELME_L FEINT_KIND_WEIHFF_KICKFEINT_NORMAL_R FEINT_KIND_DOUBLETOUCH_BALLROLL_STEPOVER_R FEINT_KIND_ROULETTE_AXISBACK_L DECIDE HALFTIME cpk_dat/common/match/path_to_glory_replay/path_to_glory_replay_01.trep cpk_dat/common/match/path_to_glory_replay/path_to_glory_replay_02.trep MenuAlertEvCompeTourPvp EvCompeEventList EvCompeEventRanking MatchTeamSelectExhibition MenuCampaignPassFreeNormalMenu MenuCampaignPassPackMissionMenu MyClubDraftDetailView CmdTaskRecvCampaignPassReward MyClubMyTeamPla

OFFSET=0xab551e TERM=HALFTIME
CONTEXT=atchRecordHeaderType m_fMatchRecordAwayUserInfo m_isComMatch EMatchCategory::CATEGORY_MYCLUB_ROOM_1vs1 EMatchCategory::CATEGORY_MYCLUB_ROOM_3vs3 MyClubPaymentKind::PAYMENT_KIND_ADVERTISEMENT EOnlineMultiplayMenuOrder::ONLINE_MULTIPLAY_MENU_HALFTIME m_isAlreadySet m_materialKeyBG IsDisableAvatarIdBG SetFriendStatusBP pTextStatus EPlayerConditionType::CONDITION_TYPE_LIVE_NONE teamBackEmblemPath GetDebugDispInfoCardInfo IsForceLightCardList LoadFileMediaObject LoadFileMovieObject isPhotoExist ref1 PlayerCardTestData EMenuMyClubPlayerDetailHexParamInfoSelect::MENU_MYCLUB_PLAYER_DETAIL_HEX_PARAM_INFO_SELEC

OFFSET=0xac606c TERM=HALFTIME
CONTEXT=eMultiTouch m_uiLock EUMGPlayerLogType::FloatRunner CallbackFinishedAfterMatch50 ECenterViewChoiceType::NONE EUserCompeEditPanelDisplayType::User AdvertisementItemFlow__DelegateSignature CallbackCmd medalNum AnalystAdviceListOpenFrom::FROM_HALFTIME SetupParam CallbackCommandSetCampaignPassDisplayed m_normalTypeCtrl ECampaignPassTaskListSegment::CampaignPass OnEnd0_100Anim MenuCenterViewNarrowDownAMResetButtonDelegate__DelegateSignature SetEventInfo viewingId EDetailViewParamExplainType::PARAM_EXPLAIN_TYPE_PLAYER_AI_PLAYSTYLE EDetailViewParamExplainType::PARAM_EXPLAIN_TYPE_PLAYER_ADD_POSITION playStyle

OFFSET=0xae6689 TERM=HALFTIME
CONTEXT=L LANG_MEX SCENE_TO_MATCH RANGE_ENTRY FLY 3RD_QUALIFY QUALIFY_PLAYOFF CUP_EURO CUP_CHL_SP LG_SPA1 LG_NET DRIBBLE_SUCCESS SET_FK SET_KICKOFF_HALF LINKAGE_L_PASSER WEAK_FOOT_ACCURACY TOO_LONG OUT_UP THROWAWAY_UP SA_TV1 FLOW_RESULT_SHOOT KIND_HALFTIME NUM_SEC_REMAIN_CUT GOLAZO NET_DEFENCE ENTERDEMO CUP_PRE_KNOCKOUT NO_COMPENAME STAGE_2ND MILESTONE NUM_EVERY_N_SCORES USERCOMPE DF_THROUGH FAST IN_A_ROW DRIBBLE_POWER RESULT_SNEAKED_THROUGH_DF FREE_ROAMING DARTING_RUN A1_PLAYER3 A1_LP_POB CHANT_CALL_TEAM BGM_CALL_SOME_KIND LARGE_HOME CheersVol_ReactBig 30_MAIN SE_ENTER_THE_STADIUM Def_Sound_Sys_MatchInfo_Ena

OFFSET=0xb4bdbb TERM=HALFTIME
CONTEXT=electedIndex IsInRoom ELayoutMatchRoomMainMenuCoopIcon HeadlineStr RandomStr Btn3Ptr ELobbySideSelectSideAnime::SetHome numStr EMenuMailboxSortType::MAILBOX_SORT_NUM forceDisp SortNewsInfoList includeFailure EMatchDemoType::MATCH_DEMO_TYPE_HALFTIME m_initialSelectIndex goldSize EPauseCameraType::PAUSE_CAMERA_TYPE_LIVE_BROADCAST m_cameraStrId m_homeTitleStr m_homeItems GetSelectableBallIdList pk GetSubstitutionsFromIndex EMatchSettingsRadarIconColor::MATCH_SETTING_RADAR_ICON_PINK m_isUseIcon EMenuMatchSettingsScreen::SCREEN_CONCEPT_ARRANGEINFO EMenuMatchSettingsRegulation::REGULATION_BALL GetMatchScree

OFFSET=0xb91a38 TERM=HALFTIME
CONTEXT=ionAudienceSdConfig CheckMatchMeaning CheckLeagueRankVariousData SoundTarget FreeKickArea KnockoutRoundKind SoundSpConditionLooseBall ExFunction ShootResultSituation MatchUpSituation MYSET_02 NEXT_PK FAR ADVANTAGE SCENE_PICKUP_RARITY AFTER_HALFTIME RAREA_B FROM_SIDE CUP_FRA CUP_CHL CUP_SUD CUP_THA_SP LG_BRA LG_MEX LG_KONAMI PLAYOFF_D2_ITA GK_JUDGMENT RATIO_AT_LEFT RATIO_AT_COUNTER INTERRUPT_OF KIND_PICKUP_HTT IS_FINAL FAILED_PLAYOFF ON_PITCH CUP_NOT_SP NUM_LOSE LOSE_ALL JUDGED ACCUMULATE_FATIGUE PCFP 04A_ADMIT OUTOF_KEEP_PLAYER COMBATIVE_SPIRIT PHENOMENAL_PASS CROSSER PRI A1_LP_PZA CHANT_STOP_BASE SHO

OFFSET=0xbcbfb9 TERM=HALFTIME
CONTEXT=PreArgs CheckDemoActionMoment CheckTime CheckBallTouchKindHistory CheckRemainingTimeNowHalf CheckPlayerSkillId CompetitionKindEx FAILED_ATTACK COMMENT_ETC OPP_SIDE KNOCKOUT_ROUND_SFINAL_FINAL LANG_WITH_ARTICLE NOGOAL_START UNI_SELECT START_HALFTIME CB OFFENCE_CHANCE TO_FAR 1ST_QUALIFY CUP_ENG CUP_ACL2 CUP_NET_SP INDIRECTFREEKICK LAST_SHOOT_COURSE RATIO_GET_STOLEN NUM_TARGET NUM_CHECK NUM_BASEID LEAGUE_OR_CUP CUP_PRE_KNOCKOUT_NOT_PLAYOFF 4Q NUM_PREMATCH_SCORE LEGEND EPIC IS WEIGHTED_PASS PK_KICKER FOX_IN_THE_BOX A1_TEAM5 A1_LT_TNA SEQ_GOAL KICKOFF_START MIDDLE_HOME LARGE_AWAY Def_Sound_Sys_Preset_Volum

OFFSET=0xa44e21 TERM=FullTime
CONTEXT=tModeChanged InAccel0 MaxSwimSpeed ServerLastTransformUpdateTimeStamp PendingForceToApply bNetworkMovementModeChanged DumpPartyState ViewActor DebugCameraControllerRef ShowProgress AngularDriveConstraint PriAxis2 LinearDrive AsyncLoadingUseFullTimeLimit LevelStreamingComponentsUnregistrationGranularity ExternalCurve AdjustVibrance BakedStringCustomAttribute ColumnName DataTableCategoryHandle SrcActorDesiredOffset SpokenText SetOcclusionMaskDarkness TraceDistance EDVLF_XZ EDVLF_MAX FrustumEndDist OnParticleBurst PackagesToFullyLoad NavigationSystemConfigClass VertexColorViewModeMaterial_ColorOnly Inval

OFFSET=0x9c8fa5 TERM=MatchResult
CONTEXT=n/CrowdNoise/Tree/ SE_AMBIENT_NORM SE_A_AMBIENT_EXCITE SA_C_NMB_E09 SA_C_NMB_E11 SA_C_NMB_E41 SA_C_NMB_E45 SA_C_NMB_E82 SA_C_NMB91 SA_C_NMB94 SE_ROOT sq_config.bin Error reading Attributes. A1_PP1 A1_PPD TreeId SetTargetSpMessageBoard CheckMatchResult CheckRatioStatsDataNumHalf CheckStealKind BallTouchKind ModeType PlayerRoleVariousData TOOK_BALL HAND_R LICENSE CUT_PHOTOGRAPHY RANGE_NATIONAL_A 04_C AREA_B2 FIELD_PENALTY_ENE SIDECHANGE2 CUP_EL LG_MAR PLAYOFF_D2_SPA CENTERING_SUCCESS REDCARD OVER_AREA_C LAST_FROM_PASS NUM_TO_KEEP NUM_CHANCELV CATCHING PROMOTION TIGHT_SCHEDULE SA_TV2 CUT_LAST CAPTAIN PLAYAB

OFFSET=0xa1324f TERM=MatchResult
CONTEXT=gs CmdStartUserCompeMatch.php FRIEND_REQUEST_BY_MYSELF is_parent_agreed Coin_03 utocFileSize SKP CLS SMV TaskEvCompeGetEventCompeCampaignRanking TaskMatchCommissioner TaskSyncManager m_attackCoach m_oppCondition TaskSyncSideSelect SuspendedMatchResult CMD_CHECK_STRING CMD_GET_LIVEUPDATE_VERSION_INFO ERR_ALREADY_WAREHOUSE TaskGetRanking ChipShotControl AcrobaticFinishing ()[B P2P_ADHOC_UNKNOWN_HIGH_LEVEL TxBpsRecentBasicStatisticsMaxSize CorrectionRiseDeterminationTimeMsThresholdLow AppYieldIdleThreadResponseThreshold Xiaomi/M2103K19C|Xiaomi/M2101K7AG|Xiaomi/M2101K7AI P2pBufferCriticalConditionTimeMs Turn

OFFSET=0xa5db22 TERM=MatchResult
CONTEXT=HANGE BALL_KEEP IN_PLAY FEWMIN TEAMAI_A BallPersonStaticMesh_12 cpk_dat/common/match/tutorial_replay/tutorial_replay_dribbling_01.trep MenuSettingsVersionInfo %u-%u-%u CmdGetEventListAndLogForAnnounceView FriendList LobbyDivideCoopTeam MenuMatchResultCoopStats OnlineEventCompeTeamSelect MenuCampaignPassFreeAfterMenu MenuCampaignPassMapNormalMenu MyClubAchievementLoginBonusList RegistSquadCmd MyClubTeamSettings CmdSetLeaguePerformanceDisped MyClubEntryInfoAlertRecommendTeam SaveEntryTeam msg2 AiMatching RehearsalMenuWindow SaveDataDeleteCategorySel CmdExchangeSeasonPointItem SettingsViewBase IsEndTimeSale

OFFSET=0xa611c1 TERM=MatchResult
CONTEXT=NMB_E86 SA_C_NMB_E93 SA_C_NMB19 SA_C_NMB24 SA_C_NMB30 SA_C_NMB39 SA_C_NMB66 SA_C_NMB74 &#x%02X; THOME SA_TGG ON Conversation CheckDirectingDemo CheckVersionTag CheckCommentaryCallExistForMessageBoard CheckSequenceData CheckMatchStatus CheckMatchResultSameOnematchAndTotal CheckMatchStatisticsVariousDataScore CheckMatchStatusStart CheckGoalDist CheckConcept CheckMatchCombination CheckCompetitionID DirectionForSound CrossFailedSituation SdSupporterTree INJURY SCORED KNOCKOUT_ROUND_2 DERBY LANG_TENSION_H_GOAL 33 WF CF EX1ST SIDE_R FIELD_EARLY_CROSS TO_NEAR CUP_RUS_SP CUP_COL_SP LG_CHE SHOOT_SUCCESS END_HALF 

OFFSET=0xa78d62 TERM=MatchResult
CONTEXT=ta/Widget/Mode/eFWorld/ManagerDetail/ManagerDetail.ManagerDetail_C Online/EvCompe/MlEvent/MenuMlEventChampionDemo /Game/Assets/ui/Data/Widget/Match/Screen/MatchMenuMLEvent/MatchMenuMLEvent.MatchMenuMLEvent_C GamePlan/CoachLink Match/Result/MatchResultCoopCommendationFromResult Online/UserCompe/Settings/MenuUserCompeSetRegulationsOnEntry /Game/Assets/ui/Data/Widget/General/Modals/GameplanCustom/GamePlanCustom.GamePlanCustom_C MyClub/MyTeam/WarehousePlayerDetail /Game/Assets/ui/Data/Widget/General/List/ObjectiveList/ObjectiveList.ObjectiveList_C Settings/UserInfo/emoji/MenuCustomizeEmoji CreateScrollTextWi

OFFSET=0xa798a4 TERM=MatchResult
CONTEXT=ate::UE_AGING_STATE_MATCH_MYCLUB_LEAGUE physical drible Conv_StrToArgInfo GetRuntimeTextureForImportUniform IsAging IsEditCompeLogo IsPadVibrationEnabled ReloadUniformParameterSingle nationalList reg AwayKind socks DebugGCRequest SetEvCompeMatchResult m_handMesh MyObject PesCameraComponent AddInt3To_DirClipMasksArray SetIsmCustomDataBy2FloatArrays InInt3 EVipPlayerControllerRequest::None EVipPlayerControllerRequest::CreateDone IsReadySMW HighSetting radius DirtyMergedMesh LoadUniSocks ETimeOfDayForEdit::DayTime set EPesPlatformCategory EPauseAnimFlags::NoPerBoneMotionBlur SetTargetByIndex ESettingMenuIco

OFFSET=0xa84183 TERM=MatchResult
CONTEXT=ial_replay_passing_01.rep cpk_dat/common/match/tutorial_replay/tutorial_replay_through_pass_04.trep FameDetailView General Mode/MenuSystem/PopChildWithInterruption/ListPopChildWithInterruption EulaAgree EvCompeAnnounceViewCompe MailboxBase MatchResultHalfTime MatchSugorokuPlayerList MenuMyClubAchievementTypeDownloader CmdUseMyclubStandardDraft ChangeSquadListAlertTitle CompletePurchase EditNGAlertNameButton SettingsVisualQuality cpk_dat/common/credit/credit.bin SettingsSupport PrepareData CancelAge SystemAlertType HistoryCol5 SpecialPlayer_3 AILeague_1 data_list CmdSuccessAdvertisement CmdGetUserCompeObs

OFFSET=0xab2d41 TERM=MatchResult
CONTEXT=erDetail/UserDetail.UserDetail_C Online/EvCompe/MlEvent/Management/MenuMlEventManagementFreePlayerDetail /Game/Assets/ui/Data/Widget/Mode/Event/TournamentMatch/TournamentMatch.TournamentMatch_C /Game/Assets/ui/Data/Widget/General/MatchFlow/MatchResultCoop/MatchResultCoop.MatchResultCoop_C MyClub/Pack/PackList MyClub/MyTeam/PlayerPositionTraining MyClub/Achievement/BingoList MyClub/Contract/CoachDetail MyClub/MyTeam/PlayerList [WinHeader] UWindowCmnHeader::OnSoftareReset /Game/Assets/ui/Data/Widget/Parts/Components/BG/SwitchBG_MLEvent/BgAnimeMLEvent.BgAnimeMLEvent G:/PES22HC/Dev-600Series/UE/UE4.26_eFB_

OFFSET=0xab2d51 TERM=MatchResult
CONTEXT=ail.UserDetail_C Online/EvCompe/MlEvent/Management/MenuMlEventManagementFreePlayerDetail /Game/Assets/ui/Data/Widget/Mode/Event/TournamentMatch/TournamentMatch.TournamentMatch_C /Game/Assets/ui/Data/Widget/General/MatchFlow/MatchResultCoop/MatchResultCoop.MatchResultCoop_C MyClub/Pack/PackList MyClub/MyTeam/PlayerPositionTraining MyClub/Achievement/BingoList MyClub/Contract/CoachDetail MyClub/MyTeam/PlayerList [WinHeader] UWindowCmnHeader::OnSoftareReset /Game/Assets/ui/Data/Widget/Parts/Components/BG/SwitchBG_MLEvent/BgAnimeMLEvent.BgAnimeMLEvent G:/PES22HC/Dev-600Series/UE/UE4.26_eFB_600/Engine/Sourc

OFFSET=0xab2d61 TERM=MatchResult
CONTEXT= Online/EvCompe/MlEvent/Management/MenuMlEventManagementFreePlayerDetail /Game/Assets/ui/Data/Widget/Mode/Event/TournamentMatch/TournamentMatch.TournamentMatch_C /Game/Assets/ui/Data/Widget/General/MatchFlow/MatchResultCoop/MatchResultCoop.MatchResultCoop_C MyClub/Pack/PackList MyClub/MyTeam/PlayerPositionTraining MyClub/Achievement/BingoList MyClub/Contract/CoachDetail MyClub/MyTeam/PlayerList [WinHeader] UWindowCmnHeader::OnSoftareReset /Game/Assets/ui/Data/Widget/Parts/Components/BG/SwitchBG_MLEvent/BgAnimeMLEvent.BgAnimeMLEvent G:/PES22HC/Dev-600Series/UE/UE4.26_eFB_600/Engine/Source/Runtime/Slate/

OFFSET=0xab44e2 TERM=MatchResult
CONTEXT=Area EMenuEvCompeAnnounceViewEventKind::CustomChallenge_Ai IsESportsEvent strFirstClearedGameLevel UpdateBannerTexture EMenuEvCompeMainMenuState::WaitBeforeMatchAlert EvCompeEventMatchSettingInfo m_strBody GetMissionRewardInfo GetTaskBeforeMatchResult IsFinishedOnlinePrivilegeCheck EMenuEvCompeEventRankingState::Loop flexAction strFile IsDefault availableBalanceStr expirybody EGamePlanCustomPlayerIconType::EXP_UP_AND_RECOMMEND m_isSwapReserve ExecCommandTutorial GetDropPlayerIconInfo GetPlayerResSortItemList IsAuthenticTeamEvent IsDispPrevNavigationOrangeGiudeFlag IsEnableJoinChallengeEventAll IsEnableRe

OFFSET=0xac5032 TERM=MatchResult
CONTEXT=/MenuEvCompeEventCompeMainMenu /Game/Assets/ui/Data/Widget/Mode/Event/CompeCampaignRank/CompeCampaignRank.CompeCampaignRank_C /Game/Assets/ui/Data/Widget/Mode/Event/MatchMenuTournament/MatchMenuTournament.MatchMenuTournament_C Match/Result/MatchResultCoopStatsFromHalfTime Online/Lobby/StrikeArena/MenuStrikeArenaPlayerSelect Match/Result/MenuMatchResultUserList Online/UserCompe/MenuUserCompeEntryLobby MyClub/MyTeam/PlayerSkillTraining MyClub/Contract/AgentList MyClub/Contract/PlayerDetailMobile Online/Season/MenuSeasonPointMenu Settings/Help/MenuSettingsTipsDetail Settings/UserInfo/MenuSettingsUserPersona

OFFSET=0xac5099 TERM=MatchResult
CONTEXT=nk.CompeCampaignRank_C /Game/Assets/ui/Data/Widget/Mode/Event/MatchMenuTournament/MatchMenuTournament.MatchMenuTournament_C Match/Result/MatchResultCoopStatsFromHalfTime Online/Lobby/StrikeArena/MenuStrikeArenaPlayerSelect Match/Result/MenuMatchResultUserList Online/UserCompe/MenuUserCompeEntryLobby MyClub/MyTeam/PlayerSkillTraining MyClub/Contract/AgentList MyClub/Contract/PlayerDetailMobile Online/Season/MenuSeasonPointMenu Settings/Help/MenuSettingsTipsDetail Settings/UserInfo/MenuSettingsUserPersonalInfo Settings/LegalPrivacy/MenuLegalPrivacy TransitionBG_Implementation Img_AvatarBG G:/PES22HC/Dev-60

OFFSET=0xad04dc TERM=MatchResult
CONTEXT=ctListener GamePlanTsak CmdSetEventGameplan CmdSetAnalystAdviceList DebugCommandExecuter Online/Lobby/MenuLobbyCreateRoomSettings Online/Lobby/MenuLobbyMatchingRoom MyClub/MyTeam/PlayerInheritPlayerList Shop/Coin/MenuShopCoin LobbyRoomList MatchResultTimeUpDemo MenuMatchSettings MatchPassPlayerList MenuMyClubAcquireableBingoList MenuMyClubOverwriteBingoList MyClubEntryMobileTeamSelect ISDispCareerplanAllocateTypeSelectView CanPopupPushNotificationPermission GetDirectAlertProgressText QMyClubTestVoid EditAlertBody PersonalizeSetting ChoiceKey FameSettingView IsNeedRedrawForResult Redraw ConfirmAge PageTit

OFFSET=0xad3971 TERM=MatchResult
CONTEXT=er_C LoadPlayers" SaveDownload0DeleteTask SD Def_Sound_Commentary_Language_Enable A1_BT0_02 SU_14_A SA_C_NMB_E43 SA_C_NMB_E87 SA_C_NMB31 SA_C_NMB44 SA_C_NMB75 MinorVersion Chant SA_TSU SetPrivateFlagForConfigMessageBoard CheckBallKeep CheckMatchResultDetail CheckScoresDetail CheckDifferenceScores CheckConditionForFoul CheckRatioStatsDataNumOtherKind CheckStatsDataNumForPlayer CheckFoulKindDetail CheckDistEnemyGK CheckConditionPassSdConfig TargetSideForSound ImportanceMatchKind LooseBallVariousData RestartStep MYSET_10 EXCITE OFFENCE POWERFUL SCENE_LINEUP1 ANY GIVEUP RAREA_A OFFENCE_MID_3RD TO_FRONT CUP_A

OFFSET=0xafe262 TERM=MatchResult
CONTEXT=Collpased. Intro/MenuIntroSurveyAfterLogin Online/Lobby/MenuLobbyRoomFriendList Online/EvCompe/MlEvent/MenuMlEventAssetPreview Online/EvCompe/MlEvent/Match/MenuMlEventFixtureResult Online/StrikeArena/MenuStrikeArenaSelectMode Match/Result/MatchResultStrikeArenaCommendation Online/Season/MenuSeasonPointTrainer BarcelonaBuild/MenuBarcelonaBuildCredit %s RenderTransform SBackgroundBlurCustom CreateBGWidgetByZOrder [AWindowManager::HasEndingChildren] m_childWindowsEnding size[%d] [Vip] RequestVipReleaseToVipController, UPesStreamingMovieWidget::CloseImpl FrameInReturnEnd OnSoftwareResetAfter teamID EA

OFFSET=0xaffa49 TERM=MatchResult
CONTEXT=lEventPoint EDataLinkageResult::DATA_LINKAGE_RESULT_LINKED_OTHER EDataLinkageResult EDataTransitionStatus::DATA_TRANSITION_STATUS_FINISHED EMenuEulaAgreeFlowEvent::NOT_AGREE MenuEvCompeAnnounceViewRewardInfo EMenuEvCompeMainMenuSelectKind::MatchResult IsDispSmartAssistSettingAlert SetFlagPopupRecordEventBeforeMatchView alertInfoList isTour controlStyleFilter GetSimModeIndex InitCursorIndex EGamePlanCustomPlayerIconType::EXP_UP m_pid m_isNotAvailable GetTeamPotentialChange IsValidPlayer RestoreGamePlanCustomResScrollPos column EGamePlanCustomPlayerResListColumn::PLAYER_RES_LIST_COLUMN_5 EGamePlanCustomTea

OFFSET=0xb1c810 TERM=MatchResult
CONTEXT=amePlanPlayerInstructionsDetailView CmdSetUserFame EvCompeAnnounceViewDownloader EvCompeFastGoalRankingGlobal Exhibition/ExhibiTeamSelect Online/League/MenuLeagueComRanking CmdCancelMatching cpk_dat/test/tex/StadiumBill_ HomeTeamSponsorTex MatchResultUserList achievementList /Game/Assets/ui/Data/Widget/Parts/Icon/CmnIconOffenseDefense/Tex1080/CmnIconOffense_Large.CmnIconOffense_Large CmdResetMyclubAgent SE_DIALOG_TICKET_USED MyClubMyTeamPlayerTrainingPosition ChangeSquadListAlertBody LiveData ShopCoinAgeConfirm BODY PROGRESSTEXT SelectedTeamName RequestDownload SettingsHelp MainMenuRecruit IsNeedExitShop

OFFSET=0xb36ea6 TERM=MatchResult
CONTEXT=aitStrLength StartShowAnimation DesiredSide Text_Bonus_Value MatchMenuStrikeArenaBtnRoomSetting Img_Qr DrawClose Text_TotalValue UiStaminaGauge sound G:/PES22HC/Dev-600Series/UProject/PesMobile/Source/PesShared/Game/Menu/Match/Result/UCMenuMatchResultCoopCommendationBase.h CallbackSettingView ToolTip_Off Alignment_Center Parts_Flag_4 CampaignPassPointGuage_Red_1 CampaignPassPointIcon_Red_2 BingoPartsLineRewardCellDetail_5 Reward_Show TileSelectBingoPartsReward_4 OnClosedAlert SwitchTactics Player_TotalMatches Text_Sort_Action ActionDone C_Manager CloseOneTimeView AgentTypeImageDownloader /Game/Assets/ui/

OFFSET=0xb39383 TERM=MatchResult
CONTEXT=rt EMenuEvCompeAnnounceViewEventKind::Preset isPostEvent rewardList strLevel EMenuEvCompeMajorCategory::MAX EMenuEvCompeEventListBeforeProceedStep::Confirm EMenuEvCompeEventListBeforeProceedStep IsMyClubGameMode m_tourInfo ClearEvCompeEventMatchResult GetChallengeEventFirstAlertInfoList callback ReleaseKonamiidTask EExchangeType pointStr GetDetailView EGamePlanAutoPlacementType::EVENT_THEME_LINK ELinkAnimeLoop::LOOP_1 m_isCaptain GetPlayerActionViewSuspensionType GetPlayerCardData GetPlayerIconInfoPitch GetPositionAptitude HasScreenShot IncreasePlayerAptitudeIcon IsExistVoidPlayer IsProgressUserStepUp Is

OFFSET=0xb8e547 TERM=MatchResult
CONTEXT=tutorial_replay/tutorial_replay_through_pass_01.trep cpk_dat/common/match/tutorial_replay/tutorial_replay_through_pass_03.rep cpk_dat/common/match/tutorial_replay/tutorial_replay_clearing_02.trep MlEventMyTeamPlayerList LobbySearchSettings MatchResultHighlight CmdUnlockMyclubGameplayerListMax MyClubContractMenuImageDownloader PROGRESSVAL msg1 QAlertNowCancel SaveDataList SeasonRecordList GetNotificationValue Recruit UserInfoFavoritePlayerList AgeSegTitle TotalFreeKey TrainingSelect Inheritance_2 DemoPlayerBase /Game/Assets/ball/ball%03d.ball%03d ","isBack": ,"addBlackLevel":" CmdGetStadiumData CmdAcceptF

OFFSET=0xbaa67a TERM=MatchResult
CONTEXT=erDetail/PlayerDetail.PlayerDetail_C Online/EvCompe/MlEvent/MenuMlEventFans Online/EvCompe/MlEvent/Management/MenuMlEventManagementPlayerDetail Online/EvCompe/MlEvent/Management/Contract/MenuMlEventContractStandardPlayerDetail Match/Result/MatchResultCoopStatsFromResult Online/UserCompe/Settings/MenuUserCompeSetRegulationsOnCreate Online/UserCompe/MenuUserCompeRecord MyClub/Contract/MenuGotPlayerList /Game/Assets/ui/Data/Widget/General/List/ExchangeTicketList/ExchangeTicketList.ExchangeTicketList_C Settings/LegalPrivacy/MenuPrivacyNoticeWithdrawalDetail ~AFlowManager UpdateBg Active:%d , UUiCmnFooterBtnN

OFFSET=0xbbd512 TERM=MatchResult
CONTEXT=hFlick/CommandTouchFlickAdvanced_3_HighPuntKick.CommandTouchFlickAdvanced_3_HighPuntKick_C DoubleTouch Captain_On GamePlanCustomIconRental ANY2_W_754 G:/PES22HC/Dev-600Series/UProject/PesMobile/Source/PesShared/Game/Menu/Match/Result/UCMenuMatchResultCoopStatsCommendationBase.h Text_Loss_Value Tooltip_None TooltipRight Text_Tooltip_Center CampaignPassPartsTouchableWidget Parts_Card_1 Parts_Card_9 Text_Total_Value_Denominator CampaignPassMapPartsInfoReward_2_2 Bingo_UnRelease Text_QuickCounter Img_SymbolOther OnCloseSelectViewCallBack CallbackGeneralBtnAlertEvent Text_SoldOut PlayerRegistrationEffectBtn C

OFFSET=0xbd09fb TERM=MatchResult
CONTEXT=/MlEvent/Management/Contract/MenuMlEventContractMain Online/EvCompe/MlEvent/Match/MenuMlEventPlayerDetailFromUpdatePlayerExperience /Game/Assets/ui/Data/Widget/Mode/Event/CompeCampaignList/CompeCampaignList.CompeCampaignList_C Match/Result/MatchResultCoopStatsCommendationFromTimeUp Match/Sugoroku/SugorokuInfo Online/UserCompe/Settings/MenuUserCompeSetRegulations MyClub/MyTeam/MyTeamMenu MyClub/Achievement/AchievementCoachDetail ChangeSkinThemeDirect Img_AvatarImage WidgetSwitcher OnCallBack_ClosedTooTip CanLoadMenuSystemResidents ScrollBar G:/PES22HC/Dev-600Series/UE/UE4.26_eFB_600/Engine/Source/Runtime/

OFFSET=0xbe395f TERM=MatchResult
CONTEXT=a/Widget/Match/Screen/ObjectiveListView/ObjectiveListView.ObjectiveListView_C Online/EvCompe/RecordEvent/MenuEvCompeFastGoalRankingSelf /Game/Assets/ui/Data/Widget/Match/Screen/ScheduleMLEvent/ScheduleMLEvent.ScheduleMLEvent_C Match/Result/MatchResultStrikeArenaStatsCommendation /Game/Assets/ui/Data/Widget/Mode/StrikeArena/StrikeArenaReward/StrikeArenaReward.StrikeArenaReward_C MyClub/MyTeam/OriginalStadium MyClub/Contract/AssetShop/AssetShopListAssetPreview GamePlan/CoachInfo MyClub/Contract/CoachList Online/Season/MenuSeasonPointRentalPlayerDetail FlowManager::StartFadeOut [Header] HideLeft, UUiCmnHea

OFFSET=0xa07636 TERM=Winner
CONTEXT=KNOWN _r CancelFade UpdateFadeWipeHeartbeat %s call ERROR!!! level = %d TopMenu/TopMenuMatchSelect Online/BlockList/MenuBlockList Online/EvCompe/EventCompe/MenuEvCompeEventCompeGroupStageDrawCanProceed Online/EvCompe/Tournament/MenuEvCompeWinner Online/EvCompe/Tournament/MenuEvCompeCpuLevelSelectSettings GamePlan/FormationSettings Match/Settings/MatchPreview Online/UserCompe/Settings/MenuUserCompeMatchSettingsOnCreate Online/UserCompe/MenuUserCompeTournamentEdit /Game/Assets/ui/Data/Widget/Match/Screen/TournamentBracket/TournamentBracket.TournamentBracket_C MyClub/MyTeam/CoachDetail Settings/LegalP

OFFSET=0xa20385 TERM=Winner
CONTEXT=riginalURL BinaryResponse SetManualCameraFade StopAllCameraAnims DefaultOrthoWidth bClientSimulatingViewTarget ClientCommitMapChange ClientFlushLevelStreaming ClientSetCinematicMode ServerAcknowledgePossession ServerVerifyViewTarget Cap bIsWinner LevelVisibility LastSpectatorSyncLocation Sensitivity bIgnoreAlt InvertAxisKey GetBoneScaleByName PreviewMeshCollectionEntry ComponentOnInputTouchBeginSignature__DelegateSignature ComponentWakeSignature__DelegateSignature ComponentEndOverlapSignature__DelegateSignature ERendererStencilMask::ERSM_2 GetWalkableSlopeOverride K2_SphereTraceComponent bShouldIgno

OFFSET=0xa51cb6 TERM=Winner
CONTEXT=On AlertEndCallback PageRankCalculating TileViewCustom_16 Tournament_32 uiEmblem_White Text_Date uiEmblem_Black_4 Icon_EventSettings Parts_StageProgressGroup Btn /Game/Assets/ui/Data/Widget/Mode/Event/MatchMenuTournament/MatchMenuTournamentWinner.MatchMenuTournamentWinner_C CmnIconUserStatus FriendListJoinJumpBtn Text_Rating_Item DistributionParts_6 DistributionParts_10 OnClosePhaseEndAlert CallMenuChoiceAction CallMenuChoiceEmoji_UserCompe CommandClassic_Plate_Dribble_4 /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_1_Move.CommandTouchFlickAdvanced_1_Move_

OFFSET=0xa51cd0 TERM=Winner
CONTEXT=nkCalculating TileViewCustom_16 Tournament_32 uiEmblem_White Text_Date uiEmblem_Black_4 Icon_EventSettings Parts_StageProgressGroup Btn /Game/Assets/ui/Data/Widget/Mode/Event/MatchMenuTournament/MatchMenuTournamentWinner.MatchMenuTournamentWinner_C CmnIconUserStatus FriendListJoinJumpBtn Text_Rating_Item DistributionParts_6 DistributionParts_10 OnClosePhaseEndAlert CallMenuChoiceAction CallMenuChoiceEmoji_UserCompe CommandClassic_Plate_Dribble_4 /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_1_Move.CommandTouchFlickAdvanced_1_Move_C /Game/Assets/ui/Data/Wid

OFFSET=0xa8af3b TERM=Winner
CONTEXT=erCardRT_In Text_MatchName AclLogoType Emblem_Team Text_PlayerNumber_2 EventMatchTimeBest CommandPartsFingerLeft /UserColor_3 /Lamp_Success Text_PK MatchStatsAway/ ShortHide /Game/Assets/ui/Data/Widget/TVGraphics/SwitchAssets_Original/CompeWinner/CompeWinner.CompeWinner_C Time_Additional/Additional_Off Time_Additional/Additional_Show MatchTimeCardAway/RedCard_0 MemberChange_1/On MemberChange_2/On MatchTimePenaltyCard/Card_Red Img_Away_UniformColor_1 Missing ',' or ']' in array declaration \r Img_CoopEvent Icon_ExperiencePoints [%s] ChangeAnime /Game/Assets/ui/Data/Widget/General/Alert/AlertPicture_

OFFSET=0xa8af47 TERM=Winner
CONTEXT=Text_MatchName AclLogoType Emblem_Team Text_PlayerNumber_2 EventMatchTimeBest CommandPartsFingerLeft /UserColor_3 /Lamp_Success Text_PK MatchStatsAway/ ShortHide /Game/Assets/ui/Data/Widget/TVGraphics/SwitchAssets_Original/CompeWinner/CompeWinner.CompeWinner_C Time_Additional/Additional_Off Time_Additional/Additional_Show MatchTimeCardAway/RedCard_0 MemberChange_1/On MemberChange_2/On MatchTimePenaltyCard/Card_Red Img_Away_UniformColor_1 Missing ',' or ']' in array declaration \r Img_CoopEvent Icon_ExperiencePoints [%s] ChangeAnime /Game/Assets/ui/Data/Widget/General/Alert/AlertPicture_TutorialSucc

OFFSET=0xa8af53 TERM=Winner
CONTEXT=me AclLogoType Emblem_Team Text_PlayerNumber_2 EventMatchTimeBest CommandPartsFingerLeft /UserColor_3 /Lamp_Success Text_PK MatchStatsAway/ ShortHide /Game/Assets/ui/Data/Widget/TVGraphics/SwitchAssets_Original/CompeWinner/CompeWinner.CompeWinner_C Time_Additional/Additional_Off Time_Additional/Additional_Show MatchTimeCardAway/RedCard_0 MemberChange_1/On MemberChange_2/On MatchTimePenaltyCard/Card_Red Img_Away_UniformColor_1 Missing ',' or ']' in array declaration \r Img_CoopEvent Icon_ExperiencePoints [%s] ChangeAnime /Game/Assets/ui/Data/Widget/General/Alert/AlertPicture_TutorialSuccess_Parts/Al

OFFSET=0xaa1382 TERM=Winner
CONTEXT=IVE_RESULT_FAIL_EXPIRED readFlag GetPresentWarehousePlayerInfo BeginPractice OnPressedRCrossDownButton OnPressedReplayNormalButton OnReleasedCrossButton GetStrAlertTimeout MenuMatchLineupData SetCreateWidget m_evaluationStr IsAnnounceGiveUpWinner GetDefaultStadiumId stadiumList MenuMatchSettingsEnvironmentData injury GetSeasonStringIdList GetTimeStringIdList GetWeatherChangeType EMenuMatchSettingsMatchTime::MATCH_TIME_7 EMenuMatchSettingsSubstitutionsCount::SUBSTITUTIONS_COUNT_2 DownloadAdFile IsSelectAchievementTypeTimeOut GetDetailViewAchievementEventInfo managerNumStr ExpiryInfo GetTitleBaseTeamS

OFFSET=0xada50d TERM=Winner
CONTEXT=esult::RECEIVE_RESULT_DETECT_REFUND EMenuMailboxReceiveResult::RECEIVE_RESULT_FAIL_UNIQUE EMenuMailboxReceiveResult OnReleasedPlayButton OnPressedAutoStopButton m_uniformNumberList BPLog GetCurrentCameraType m_awayTitleStr SetAnnounceGiveUpWinner GetMatchTimeKind EMatchSettingsRadarIconColor::MATCH_SETTING_RADAR_ICON_DEFAULT EMatchSettingsRadarIconColor::MATCH_SETTING_RADAR_ICON_BLACK GetInactiveTimeIndexList SetStadiumSettings settingsData GetMatchTimeStringId IsOnceSucess TimeCautionStr Coach IsChallengeRecv secondary gp GetViewStr cancelStrId nowLevelDigits GetFooterInfoMobile isTutorial2 m_param

OFFSET=0xb36ca1 TERM=Winner
CONTEXT=oduction Texture_Other CheckMark_On Text_Achieved VerticalBoxCustom_71 TileViewCustom_5 Choice_5 Status_Club /Game/Assets/menu/dialog/AlertDialog/BP_MenuAlertImageDialogRentalPlayer.BP_MenuAlertImageDialogRentalPlayer_C SetStrFailure Emb_4 WinnerChoice Callback_CompeEventClearAlert Text_Header Text_NextReward Text_Reward_MainOnly Icon_Settings TileViewCustom_Segment Text_CollectiveStrength OnPlayStarted /Game/Assets/ui/Data/Widget/General/Alert/AlertCreativeLeague/AlertCreativeLeague.AlertCreativeLeague_C StartWaitStrLength StartShowAnimation DesiredSide Text_Bonus_Value MatchMenuStrikeArenaBtnRoomS

OFFSET=0xbe4ad6 TERM=Winner
CONTEXT=back CampaignPassMenuType::CAMPAIGN_PASS_MENU_TYPE_AFTER SortAction uniformName OnCancelCallback m_pTimeoutAlert colorB_b isCompleted m_majorCategory m_isGameLevelDisp CallbackCrossPlatformNoticeClosed m_pTileView MenuEvCompeTournamentEventWinnerData EFriendListType::FriendListTypeMax ABILITY SetUpWithMultiStrInfo EMenuLeagueType::COM_LEAGUE List1LineOnTextCommittedEmptyEvent__DelegateSignature tint ACTIONVIEW_ITEM_TYPE::ACTIONVIEW_ITEM_CHANGE PARENT_TYPE::BEFORE_CONTRACT SetEventOnShopCoinManager ESkillTrainingSegmentType CallbackSelectOneBtnDialogEvent SelectCareerplanAllocateTypeNavigationViewPos

OFFSET=0x9b9de1 TERM=Victory
CONTEXT=ewEvent/DetailViewEventText.DetailViewEventText_C Text_Add CallbackAlertForDecideRejectAll uniform_number_edit /Game/Assets/menu/online/lobby/RoomMainMenu/SendUserComment/BP_MenuRoomSendUserCommentView.BP_MenuRoomSendUserCommentView_C Text_VictoryPoint_Value EventInfo Text_AllGet_Title /Game/Assets/ui/Data/Widget/General/MainMenu/MainMenu_3/MainMenu_3.MainMenu_3_C ActionButtonPauseChoice CommandClassic_Plate_StunningShot_1 Icon_WatchingMatch Text_TotalItem UserCommendation_2 UserStats_2 ANY2_W_753 CONNECTION_REPORT_VIEW TooltipCenter Tooltip_Off Parts_Card_5 Text_Heading_Reward /Game/Assets/ui/Data/W

OFFSET=0xaeac4c TERM=Victory
CONTEXT=entMatch_Item SetupCallbackCancel /Game/Assets/ui/Data/Widget/Mode/eFWorld/TileSelecteFootballLeague/TileSelecteFootballLeague.TileSelecteFootballLeague_C StartGetLineNum SideLeader TileViewCustom_1 Icon_BonusTime Text_MatchLevel_Item Text_VictoryPoint_Item KID_PARENTAL_CONTROL Text_Attack Plate_UserCompe CommandClassic_Plate_Dribble_3 CommandClassic_Plate_Deffense Command_Feint_Smart /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/CommandTouchFlickAdvanced_1_CursorChange.CommandTouchFlickAdvanced_1_CursorChange_C /Game/Assets/ui/Data/Widget/General/MatchFlow/CommandTouchFlick/Command

OFFSET=0xb7e466 TERM=AddedTime
CONTEXT=entVariousData CheckConditionForSubstitutionSdConfig CheckMatchStatisticsVariousDataPlayer CheckActArea CheckShootResultOffenceRecord CheckCoachInstructionData CheckTeamStyle CheckSectionVariousData CheckCompeName EVENT_CONTINUE AreaTarget AddedTimeVariousData AdvantageVariousData SetplayVariousData STOP DISADVANTAGE NEAR_SIDE AREA_A1 FIELD_CIRCLE CUP_SCO CUP_TUR_SP PLAYOFF_MEX2 FK_SCORE INFRAME_SHOOT INPLAY NUM_THROUGH_ENE NUM_DASH_RATE LINKAGE_PASSER RATIO_AT_CENTER NUM_AT_COUNTER SIMILAR_GOAL NUM_LOOSE_SEC NUM_TODAY BOTTOM_CONCEDING THROWAWAY CUT_CUP FINAL_1ST 3Q NUM_DRAW SAFE_PREMATCH PERSONAL_DATA

OFFSET=0xc17ad5 TERM=AddedTime
CONTEXT=ory force_reset TaskSelectableSettingsList strikeArenaTutorial %03d RC_33 _PP2_ SA_HALF_ROOT SA_C_NMB_E25 SA_C_NMB_E33 SA_C_NMB83 SA_C_NMB93 SA_C_NMB95 sq_list.xml <! encoding SP_P%06d_%04dA A1_V2 A1_T0 A1_T0A SA_V2 A1_P0 CheckNowHalf CheckAddedTimeVariousData CheckIsForfeitedGame CheckSideBallTouchRecord CheckActAreaBackupEvent CheckDiffLineFriendTopEnemyLast CheckFreePlayerLastTurnover CheckOffenceRecordVariousData CheckPassSituationOffenceRecord CheckAreaFromWideLine CheckConditionForDribbleSdConfig ActingShootFailedLevel OffenceRecordVariousData ConceptKind TeamStyle ChallengeMatchData OUTBALL FOLL

OFFSET=0xadaf75 TERM=ExtraTime
CONTEXT=secToMsec IsLastMissionFromIndex mainmenuInfo alertBody EInfoDirectDestination::MYLEAGUE LeagueDetailViewRewardData worldRatio currentPoints IsHighDivisionPVP m_pUiText EMenuRoomDetailElement::DESIRED_CPU_LEVEL ERoomUserSide m_isInjury m_isExtraTime GetEsportsEventGetPlayerNumOfEachSide GetSelectableRoomSettingsSpRegulation GetUserCommentStr IsPresetLobby MenuPesScreenLog EMatchPassUpdateModelStep::MATCH_PASS_UPDATE_MODEL_STEP_ON EMatchPassType::MATCH_PASS_PAID MatchPassPrice m_isEnableDispAgg CallbackAnimFinishedDateToMode IsRunningSwitchAnimation EMatchCategory::CATEGORY_EVENT_RECORD MyClubPaymentKin

OFFSET=0xb75300 TERM=ExtraTime
CONTEXT=ntMoveResponsePacked ServerMoveOld OldTimeStamp JumpOffJumpZFactor MaxWalkSpeedCrouched Buoyancy LastUpdateRotation DefaultWaterMovementMode bMaintainHorizontalGroundVelocity bPerformingJumpOff CheatScript bStaticObject PriorityAsyncLoadingExtraTime LevelStreamingComponentsRegistrationGranularity AdjustBrightness SetSortOrder EGrammaticalNumber::Type SetShadowDistanceFadeoutFraction OcclusionDepthRange MinOutput Vector4Distribution ENodeEnabledState::Disabled TerminalSubCategory TerminalSubCategoryObject NodeWidth EnabledState DistFromCamera FULLYLOAD_Mutator WorldSettingsClass ShadedLevelColorationLit

OFFSET=0xb88daa TERM=ExtraTime
CONTEXT=ToggleAILogging LocString CustomChannelSetup CollisionChannelRedirects EComponentCreationMethod::UserConstructionScript OldParentTables EAngularDriveMode::TwistAndSwing ZDrive TwistLimit GetControlRotation PriorityLevelStreamingActorsUpdateExtraTime InCurve FloatAttributes GetDecalMaterial Duaration bDestroyOwnerAfterFade bIsLocalReplay SpectatorControllers FarShadowDistance bCastShadowsOnAtmosphere ETransitionType::Saving FULLYLOAD_MAX OldPluginName ScreenMessageString WorldSettingsClassName LevelColorationLitMaterial ShadedLevelColorationLitMaterialName VertexColorViewModeMaterialName_RedOnly Constra

OFFSET=0xbf921d TERM=ExtraTime
CONTEXT=DED_MATCH EInfoDirectDestination::CUSTOM_EVENT_VSAI m_isInvited currentRating promotionPointsTitleStr ERoomSettingsKind::SECTION_ROOM_SETTINGS ERoomEntryRestrictionType::ROOM_ENTRY_RESTRICTION_NONE m_isExpiredRoom m_isAdditionalSubstitutionExtraTime IsAgingRepeatReadyAndUnready IsPresetCoop EMatchPassUpdateModelStep::MATCH_PASS_UPDATE_MODEL_STEP_ANIM_HIDE EMatchPassBalloonStep::MATCH_PASS_BALLOON_STEP_IDLE EMatchPassRewardType::MATCH_PASS_REWARD_PLAYER EMatchPassRewardType::MATCH_PASS_REWARD_STANDARD_3 EMatchPassRewardType::MATCH_PASS_REWARD_STANDARD_5 EMatchPassAcquisitionStatus::MATCH_PASS_ACQUISITIO
