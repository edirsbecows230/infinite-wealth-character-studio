-- Yakuza 8 runtime Character + Costume selector.
-- Ichiban / Kiryu / Both sources with one transaction owner.
-- No debugger APIs and no live World Actor refresh.

local SCRIPT_VERSION = "1.3.0-rc1"
local GAME_PROCESS = "likeadragon8.exe"
local STATUS_RECORD_ID = 1900
local LOG_PATH = (os.getenv("TEMP") or os.getenv("TMP") or ".") ..
  "\\Yakuza8_Character_Selector.log"

local CHARACTER_HEADER_AOB = table.concat({
  "61 72 6D 70 00 00 00 00 00 00 02 00 00 00 00 00",
  "?? ?? ?? ?? 00 00 00 00 00 00 00 00 00 00 00 00",
  "96 29 00 00 03 00 00 00",
}, " ")

local COSTUME_HEADER_AOB = table.concat({
  "61 72 6D 70 00 00 00 00 00 00 02 00 00 00 00 00",
  "?? ?? ?? ?? 00 00 00 00 00 00 00 00 00 00 00 00",
  "3D 00 00 00 03 00 00 00",
}, " ")

local CHARACTER_ROWS = 10646
local CHARACTER_COLUMNS = 22
local CHARACTER_DB_ID = 0x4A6
local COSTUME_OUTER_ROWS = 61
local COSTUME_ROWS = 539
local COSTUME_COLUMNS = 7
local COSTUME_TABLE_ID = 0x1279
local COSTUME_STORAGE_MODE = 1
local COSTUME_STRIDE = 16
local PLAN = rawget(_G, "Y8_PHASE17_DUAL_PLAN")

local previous15 = rawget(_G, "Y8Phase15")
if type(previous15) == "table" and previous15.active and
   type(previous15.restore) == "function" then
  pcall(previous15.restore, "Phase 1.7 dual-source script load")
end
local previous16 = rawget(_G, "Y8Phase16")
if type(previous16) == "table" and previous16.active and
   type(previous16.restore) == "function" then
  pcall(previous16.restore, "Phase 1.7 dual-source script load")
end
local previous = rawget(_G, "Y8Phase17")
if type(previous) == "table" and previous.active and type(previous.restore) == "function" then
  pcall(previous.restore, "transaction script reload")
end
if type(previous) == "table" and previous.form then
  pcall(function() previous.form.destroy() end)
end
if type(previous) == "table" and previous.connectionTimer then
  pcall(function() previous.connectionTimer.destroy() end)
end

local S = {
  version = SCRIPT_VERSION,
  pid = nil,
  characterDb = nil,
  costumeDb = nil,
  active = false,
  activeToken = nil,
  outfitMode = nil,
  sourceMode = nil,
  selection = nil,
  backup = nil,
  customTarget = nil,
  customTargets = {},
  language = "zh",
  slotStates = {},
  editingSourceId = "ichiban",
  uiLoading = false,
  form = nil,
  controls = nil,
  visibleTargetIds = {},
  connectionTimer = nil,
  monitorPid = nil,
  monitorValidatedPid = nil,
  monitorBusy = false,
  monitorLastMessage = nil,
  monitorRetryTicks = 0,
}
_G.Y8Phase17 = S

local function hex(value)
  if type(value) ~= "number" then return "unreadable" end
  return string.format("0x%X", value)
end

local function appendLog(message)
  local file = io.open(LOG_PATH, "a")
  if not file then return end
  file:write(string.format("[%s] %s\n", os.date("%Y-%m-%d %H:%M:%S"), message))
  file:close()
end

local function updateStatus(message)
  local text = "[Infinite Wealth Character Studio] " .. tostring(message)
  local okList, list = pcall(getAddressList)
  if okList and list and type(list.getMemoryRecordByID) == "function" then
    local okRecord, record = pcall(function()
      return list.getMemoryRecordByID(STATUS_RECORD_ID)
    end)
    if okRecord and record then pcall(function() record.Description = text end) end
  end
  print(text)
  appendLog(text)
  if S.controls and S.controls.status then
    pcall(function() S.controls.status.Caption = tostring(message) end)
  end
end

local function readU32(address)
  local ok, value = pcall(readInteger, address)
  if ok and type(value) == "number" then return value end
  return nil
end

local function readU16(address)
  local ok, value = pcall(readSmallInteger, address)
  if ok and type(value) == "number" then return value end
  return nil
end

local function writeU32(address, value)
  local ok, result = pcall(writeInteger, address, value)
  return ok and result ~= false
end

local function writeU16(address, value)
  local ok, result = pcall(writeSmallInteger, address, value)
  return ok and result ~= false
end

local function readVersion(base)
  local ok, value = pcall(readBytes, base + 0x0A, 1, false)
  if ok and type(value) == "number" then return value end
  return nil
end

local function readMagic(base)
  local ok, value = pcall(readString, base, 4, false)
  if ok then return value end
  return nil
end

local function currentPid()
  local ok, pid = pcall(getProcessIDFromProcessName, GAME_PROCESS)
  if ok and type(pid) == "number" and pid ~= 0 then return pid end
  return nil
end

local function attach()
  local pid = currentPid()
  if not pid then return false, "likeadragon8.exe is not running" end
  local opened = 0
  if type(getOpenedProcessID) == "function" then
    local ok, value = pcall(getOpenedProcessID)
    if ok and type(value) == "number" then opened = value end
  end
  if opened ~= pid then
    local ok, result = pcall(openProcess, pid)
    if not ok or result == false then
      return false, "could not attach CE to game PID " .. tostring(pid)
    end
  end
  S.pid = pid
  return true
end

local function clearDeadProcessState(oldPid, reason)
  appendLog(string.format("PROCESS_END old_pid=%s reason=%s active=%s backup=%s",
    tostring(oldPid), tostring(reason), tostring(S.active), tostring(S.backup ~= nil)))
  -- The process no longer exists. Never attempt Restore against its stale
  -- addresses; the OS has already discarded every runtime modification.
  S.pid = nil
  S.monitorPid = nil
  S.monitorValidatedPid = nil
  S.characterDb = nil
  S.costumeDb = nil
  S.active = false
  S.activeToken = nil
  S.outfitMode = nil
  S.sourceMode = nil
  S.selection = nil
  S.backup = nil
  S.customTarget = nil
  S.customTargets = {}
end

local function destroyScanResults(results)
  if not results then return end
  if type(results.destroy) == "function" then pcall(results.destroy, results)
  elseif type(results.Destroy) == "function" then pcall(results.Destroy, results) end
end

local function validateCommonHeader(base, outerRows)
  if type(base) ~= "number" or base < 0x10000 then return false, "invalid base" end
  if readMagic(base) ~= "armp" then return false, "ARMP magic mismatch" end
  if readVersion(base) ~= 2 then return false, "ARMP version mismatch" end
  local rows = readU32(base + 0x20)
  local columns = readU32(base + 0x24)
  if rows ~= outerRows or columns ~= 3 then
    return false, string.format("outer layout mismatch rows=%s columns=%s",
      tostring(rows), tostring(columns))
  end
  local innerOffset = readU32(base + 0x10)
  if not innerOffset or innerOffset < 0x100 or innerOffset > 0x2000000 then
    return false, "invalid inner offset " .. tostring(innerOffset)
  end
  return true, innerOffset
end

local function sourceById(sourceId)
  if type(PLAN) ~= "table" or type(PLAN.sources) ~= "table" then return nil end
  return PLAN.sources[sourceId]
end

local function targetById(targetId)
  if type(PLAN) ~= "table" or type(PLAN.targets) ~= "table" then return nil end
  if PLAN.targets[targetId] then return PLAN.targets[targetId] end
  if type(PLAN.labTargets) == "table" and PLAN.labTargets[targetId] then
    return PLAN.labTargets[targetId]
  end
  if type(PLAN.maleTargets) == "table" and PLAN.maleTargets[targetId] then
    return PLAN.maleTargets[targetId]
  end
  if type(S.customTargets) == "table" and S.customTargets[targetId] then
    return S.customTargets[targetId]
  end
  if S.customTarget and S.customTarget.id == targetId then return S.customTarget end
  return nil
end

local function allSourceIds()
  if type(PLAN) ~= "table" or type(PLAN.sourceOrder) ~= "table" then return {} end
  return PLAN.sourceOrder
end

local function sourceIdsForMode(sourceMode)
  if sourceMode == "ichiban" then return { "ichiban" } end
  if sourceMode == "kiryu" then return { "kiryu" } end
  if sourceMode == "both" then return { "ichiban", "kiryu" } end
  return {}
end

local function sourceIsSelected(sourceId, sourceMode)
  for _, selected in ipairs(sourceIdsForMode(sourceMode)) do
    if selected == sourceId then return true end
  end
  return false
end

local function sortedRowsForSource(sourceId)
  local source = sourceById(sourceId)
  local rows = {}
  if not source or type(source.records) ~= "table" then return rows end
  for row, _ in pairs(source.records) do rows[#rows + 1] = row end
  table.sort(rows)
  return rows
end

local function fixedVariantPair(variant)
  if not variant then return nil, nil end
  local key = tonumber(variant.character)
  if not key or key == 0 then key = tonumber(variant.hawaii) end
  if not key or key == 0 then return nil, nil end
  -- Fixed Variant means one explicit *character key in every region/context.
  return key, key
end

local function validateCharacterDb(base)
  local ok, innerOrError = validateCommonHeader(base, CHARACTER_ROWS)
  if not ok then return false, innerOrError end
  local inner = innerOrError
  local rows = readU32(base + inner)
  local columns = readU32(base + inner + 0x04)
  local runtimeId = readU32(base + inner + 0x20)
  local databaseId = runtimeId and (runtimeId % 0x80000000) or nil
  if rows ~= CHARACTER_ROWS or columns ~= CHARACTER_COLUMNS or databaseId ~= CHARACTER_DB_ID then
    return false, string.format(
      "Character inner mismatch rows=%s columns=%s runtime_id=%s normalized=%s",
      tostring(rows), tostring(columns), hex(runtimeId), hex(databaseId))
  end

  local keyOffset = readU32(base + inner - 0x10)
  local mappingOffset = readU32(base + inner - 0x08)
  if not keyOffset or not mappingOffset or keyOffset >= inner or mappingOffset >= inner then
    return false, "invalid Character sorted-index offsets"
  end
  local seenPositions = {}
  for _, sourceId in ipairs(allSourceIds()) do
    local source = sourceById(sourceId)
    if not source or type(source.contextEntries) ~= "table" then
      return false, "missing Character entries for source " .. tostring(sourceId)
    end
    for _, entry in ipairs(source.contextEntries) do
      if seenPositions[entry.position] then
        return false, "duplicate Character mapping position " .. tostring(entry.position)
      end
      seenPositions[entry.position] = true
      local key = readU32(base + keyOffset + entry.position * 4)
      local row = readU32(base + mappingOffset + entry.position * 4)
      if key ~= entry.key or not row or row < 0 or row >= CHARACTER_ROWS then
        return false, string.format(
          "Character key/mapping mismatch source=%s key=%d value=%s row=%s",
          sourceId, entry.key, tostring(key), tostring(row))
      end
    end
  end
  return true, {
    base = base,
    inner = base + inner,
    keyArray = base + keyOffset,
    mapping = base + mappingOffset,
  }
end

local function validateCostumeDb(base)
  if type(PLAN) ~= "table" or type(PLAN.targets) ~= "table" or
     type(PLAN.targetOrder) ~= "table" or type(PLAN.sources) ~= "table" then
    return false, "embedded dual-source selector plan is missing"
  end

  local ok, innerOrError = validateCommonHeader(base, COSTUME_OUTER_ROWS)
  if not ok then return false, innerOrError end
  local innerOffset = innerOrError
  local rows = readU32(base + innerOffset)
  local columns = readU32(base + innerOffset + 0x04)
  local packed = readU32(base + innerOffset + 0x20)
  local tableId = packed and (packed % 0x1000000) or nil
  local storageByte = packed and (math.floor(packed / 0x1000000) % 0x100) or nil
  -- Disk high byte is 0x01; the live table is 0xC1.  Bits 7/6 are
  -- runtime-state flags, while STORAGE_MODE is the low bit only.
  local storageMode = storageByte and (storageByte % 0x02) or nil
  if rows ~= COSTUME_ROWS or columns ~= COSTUME_COLUMNS or
     tableId ~= COSTUME_TABLE_ID or storageMode ~= COSTUME_STORAGE_MODE then
    return false, string.format(
      "Costume inner mismatch rows=%s columns=%s packed=%s table_id=%s storage=%s",
      tostring(rows), tostring(columns), hex(packed), hex(tableId), tostring(storageMode))
  end

  local rowOffsetTableOffset = readU32(base + innerOffset + 0x1C)
  if not rowOffsetTableOffset or rowOffsetTableOffset <= innerOffset or
     rowOffsetTableOffset > 0x2000000 then
    return false, "invalid Costume row-offset table " .. tostring(rowOffsetTableOffset)
  end

  local rowOffsets = {}
  local previous = nil
  for row = 0, COSTUME_ROWS - 1 do
    local offset = readU32(base + rowOffsetTableOffset + row * 4)
    if not offset or offset <= innerOffset or offset >= rowOffsetTableOffset then
      return false, string.format("invalid Costume row offset row=%d value=%s", row, hex(offset))
    end
    if previous and offset - previous ~= COSTUME_STRIDE then
      return false, string.format("Costume stride mismatch row=%d previous=%s current=%s",
        row, hex(previous), hex(offset))
    end
    rowOffsets[row] = offset
    previous = offset
  end

  local playerToSource = {}
  local sourceLayouts = {}
  for _, sourceId in ipairs(allSourceIds()) do
    local source = sourceById(sourceId)
    if not source or type(source.records) ~= "table" then
      return false, "missing Costume source plan " .. tostring(sourceId)
    end
    playerToSource[source.player] = sourceId
    sourceLayouts[sourceId] = {
      sourceRows = 0, seenPlan = {}, actual = {}, state = "unknown_or_other_mod",
      knownSelection = nil, transactionSafe = false,
    }
  end

  for row = 0, COSTUME_ROWS - 1 do
    local rowAddress = base + rowOffsets[row]
    local player = readU16(rowAddress)
    local costume = readU16(rowAddress + 0x02)
    local character = readU16(rowAddress + 0x04)
    local hawaii = readU16(rowAddress + 0x06)
    if not player or not costume or not character or not hawaii then
      return false, "unreadable Costume row " .. tostring(row)
    end
    local sourceId = playerToSource[player]
    if sourceId then
      local source = sourceById(sourceId)
      local sourceLayout = sourceLayouts[sourceId]
      sourceLayout.sourceRows = sourceLayout.sourceRows + 1
      local expected = source.records[row]
      if not expected then
        return false, string.format("unexpected source row source=%s row=%d",
          sourceId, row)
      end
      sourceLayout.seenPlan[row] = true
      if costume ~= expected.costume then
        return false, string.format(
          "costume mismatch source=%s row=%d expected=%d actual=%d",
          sourceId, row, expected.costume, costume)
      end
      sourceLayout.actual[row] = { character = character, hawaii = hawaii }
    end
  end

  local function matchesOriginal(sourceId)
    local source = sourceById(sourceId)
    local actual = sourceLayouts[sourceId].actual
    for row, expected in pairs(source.records) do
      local pair = actual[row]
      if not pair or pair.character ~= expected.originalCharacter or
         pair.hawaii ~= expected.originalHawaii then return false end
    end
    return true
  end

  local function matchesTarget(sourceId, target, mode, variant)
    local source = sourceById(sourceId)
    local actual = sourceLayouts[sourceId].actual
    local sourcePlan = target.sourcePlans and target.sourcePlans[sourceId]
    if not target.fixedNpc and
       (not sourcePlan or type(sourcePlan.records) ~= "table") then return false end
    for row, _ in pairs(source.records) do
      local expectedCharacter, expectedHawaii
      if target.fixedNpc then
        expectedCharacter, expectedHawaii = target.standardCharacter, target.standardHawaii
      elseif mode == "context_matched" then
        local item = sourcePlan.records[row]
        if not item then return false end
        expectedCharacter, expectedHawaii = item.targetCharacter, item.targetHawaii
      elseif mode == "default_only" then
        expectedCharacter, expectedHawaii = target.standardCharacter, target.standardHawaii
      else
        expectedCharacter, expectedHawaii = fixedVariantPair(variant)
      end
      local pair = actual[row]
      local matches = pair and pair.character == expectedCharacter and
        pair.hawaii == expectedHawaii
      -- Accept a state left by v0.1.0 so the new script can safely back it up
      -- and replace/reset it instead of refusing the first transaction.
      if not matches and mode == "fixed_variant" and pair then
        matches = pair.character == variant.character and pair.hawaii == variant.hawaii
      end
      if not matches then return false end
    end
    return true
  end

  local function uniformFixedKey(sourceId)
    local source = sourceById(sourceId)
    local actual = sourceLayouts[sourceId].actual
    local fixedKey = nil
    for row, _ in pairs(source.records) do
      local pair = actual[row]
      if not pair or pair.character == 0 or pair.character ~= pair.hawaii then
        return nil
      end
      if fixedKey == nil then fixedKey = pair.character end
      if pair.character ~= fixedKey then return nil end
    end
    return fixedKey
  end

  local unknownDetails = {}
  local allSafe = true
  local totalSourceRows = 0
  for _, sourceId in ipairs(allSourceIds()) do
    local source = sourceById(sourceId)
    local sourceLayout = sourceLayouts[sourceId]
    totalSourceRows = totalSourceRows + sourceLayout.sourceRows
    if sourceLayout.sourceRows ~= source.rowCount then
      return false, string.format(
        "source row count mismatch source=%s expected=%d actual=%d",
        sourceId, source.rowCount, sourceLayout.sourceRows)
    end
    for row, _ in pairs(source.records) do
      if not sourceLayout.seenPlan[row] then
        return false, string.format("missing planned source row source=%s row=%d",
          sourceId, row)
      end
    end

    if matchesOriginal(sourceId) then
      sourceLayout.state = "original"
      sourceLayout.transactionSafe = true
    else
      for _, targetId in ipairs(PLAN.targetOrder) do
        local target = PLAN.targets[targetId]
        if matchesTarget(sourceId, target, "context_matched", nil) then
          sourceLayout.state = targetId .. "/context_matched"
          sourceLayout.knownSelection = { targetId = targetId, mode = "context_matched" }
          sourceLayout.transactionSafe = true
          break
        elseif matchesTarget(sourceId, target, "default_only", nil) then
          sourceLayout.state = targetId .. "/default_only"
          sourceLayout.knownSelection = { targetId = targetId, mode = "default_only" }
          sourceLayout.transactionSafe = true
          break
        else
          for variantIndex, variant in ipairs(target.variants or {}) do
            if matchesTarget(sourceId, target, "fixed_variant", variant) then
              sourceLayout.state = targetId .. "/fixed_variant/" .. tostring(variantIndex)
              sourceLayout.knownSelection = {
                targetId = targetId, mode = "fixed_variant", variantIndex = variantIndex,
              }
              sourceLayout.transactionSafe = true
              break
            end
          end
          if sourceLayout.transactionSafe then break end
        end
      end
    end
    if not sourceLayout.transactionSafe then
      local fixedKey = uniformFixedKey(sourceId)
      if fixedKey then
        sourceLayout.state = "uniform_fixed_key/" .. tostring(fixedKey)
        sourceLayout.knownSelection = { fixedKey = fixedKey }
        sourceLayout.transactionSafe = true
      end
    end
    if not sourceLayout.transactionSafe then
      allSafe = false
      for _, row in ipairs(sortedRowsForSource(sourceId)) do
        if #unknownDetails >= 12 then break end
        local pair = sourceLayout.actual[row]
        unknownDetails[#unknownDetails + 1] = string.format(
          "%s/row%d=%d,%d", sourceId, row, pair.character, pair.hawaii)
      end
    end
  end

  local layout = {
    base = base,
    inner = base + innerOffset,
    rowOffsetTable = base + rowOffsetTableOffset,
    rowOffsets = rowOffsets,
    sourceRows = totalSourceRows,
    sources = sourceLayouts,
    unknownDetails = unknownDetails,
    transactionSafe = allSafe,
  }
  return true, layout
end

local function scanOne(pattern, label, validator)
  local okScan, results = pcall(AOBScan, pattern, "-X*W*C")
  if not okScan or not results then return false, label .. " header AOB not found" end
  local count = tonumber(results.Count) or 0
  appendLog(string.format("SCAN label=%s hits=%d", label, count))
  local matches = {}
  for index = 0, count - 1 do
    local hit = tonumber(results[index], 16)
    if hit then
      local valid, layoutOrError = validator(hit)
      if valid then
        matches[#matches + 1] = layoutOrError
      else
        appendLog(string.format("REJECT label=%s hit=%s reason=%s",
          label, hex(hit), tostring(layoutOrError)))
      end
    end
  end
  destroyScanResults(results)
  if #matches == 0 then return false, "no validated " .. label .. " block" end
  if #matches > 1 then
    local bases = {}
    for _, item in ipairs(matches) do bases[#bases + 1] = hex(item.base) end
    return false, "multiple validated " .. label .. " blocks: " .. table.concat(bases, ", ")
  end
  return true, matches[1]
end

function S.validateAll()
  local okAttach, attachError = attach()
  if not okAttach then
    updateStatus("ERROR: " .. tostring(attachError))
    return false, attachError
  end

  updateStatus("locating Character DB...")
  local okCharacter, characterOrError = scanOne(
    CHARACTER_HEADER_AOB, "character_character_data", validateCharacterDb)
  if not okCharacter then
    updateStatus("ERROR: " .. tostring(characterOrError))
    return false, characterOrError
  end
  S.characterDb = characterOrError

  updateStatus("Character DB OK; locating Costume DB...")
  local okCostume, costumeOrError = scanOne(
    COSTUME_HEADER_AOB, "character_costume", validateCostumeDb)
  if not okCostume then
    updateStatus("ERROR: " .. tostring(costumeOrError))
    return false, costumeOrError
  end
  S.costumeDb = costumeOrError

  local states = {}
  for _, sourceId in ipairs(allSourceIds()) do
    local sourceLayout = S.costumeDb.sources[sourceId]
    states[#states + 1] = sourceId .. "=" .. tostring(sourceLayout.state)
  end
  local warning = S.costumeDb.transactionSafe and "" or
    " | WARNING: at least one source is not transaction-safe"
  updateStatus(string.format(
    "READY v%s | Character=%s | Costume=%s rows=%d states=[%s]%s",
    SCRIPT_VERSION, hex(S.characterDb.base), hex(S.costumeDb.base),
    S.costumeDb.sourceRows, table.concat(states, ", "), warning))
  appendLog(string.format(
    "LAYOUT pid=%d character_inner=%s character_mapping=%s costume_inner=%s costume_offsets=%s",
    S.pid, hex(S.characterDb.inner), hex(S.characterDb.mapping),
    hex(S.costumeDb.inner), hex(S.costumeDb.rowOffsetTable)))
  if #S.costumeDb.unknownDetails > 0 then
    appendLog("UNKNOWN " .. table.concat(S.costumeDb.unknownDetails, "; "))
  end
  return true
end

local function parseNumericKey(value)
  local textValue = tostring(value or ""):gsub("^%s+", ""):gsub("%s+$", "")
  local number = tonumber(textValue)
  if not number and textValue:match("^0[xX][0-9a-fA-F]+$") then
    number = tonumber(textValue:sub(3), 16)
  end
  if not number or number ~= math.floor(number) or number <= 0 or number > 0xFFFFFFFF then
    return nil
  end
  return number
end

function S.prepareCustomTarget(value)
  local key = parseNumericKey(value)
  if not key then return false, "enter a positive decimal or hexadecimal Character key" end
  for _, sourceId in ipairs(allSourceIds()) do
    for _, entry in ipairs(sourceById(sourceId).contextEntries) do
      if entry.key == key then
        return false, "that is a source context key; enter a target *character key"
      end
    end
  end

  local okAttach, attachError = attach()
  if not okAttach then return false, attachError end
  local layout = nil
  if S.characterDb and S.characterDb.base then
    local valid, result = validateCharacterDb(S.characterDb.base)
    if valid then layout = result end
  end
  if not layout then
    local okLocate, result = scanOne(
      CHARACTER_HEADER_AOB, "character_character_data", validateCharacterDb)
    if not okLocate then return false, result end
    layout = result
  end
  S.characterDb = layout

  local low, high = 0, CHARACTER_ROWS - 1
  local position = nil
  while low <= high do
    local middle = math.floor((low + high) / 2)
    local candidate = readU32(layout.keyArray + middle * 4)
    if candidate == nil then return false, "could not read Character key array" end
    if candidate == key then
      position = middle
      break
    elseif candidate < key then
      low = middle + 1
    else
      high = middle - 1
    end
  end
  if position == nil then return false, "Character key not found: " .. tostring(key) end
  local row = readU32(layout.mapping + position * 4)
  if row == nil or row < 0 or row >= CHARACTER_ROWS then
    return false, "invalid Character Row for key " .. tostring(key)
  end

  local id = "custom_key_" .. tostring(key)
  S.customTarget = {
    id = id,
    label = string.format("[Custom Key / 自定义] key %d -> row %d", key, row),
    targetRow = row,
    standardCharacter = key,
    standardHawaii = key,
    fixedNpc = true,
    variants = {{
      id = id,
      label = string.format("Custom key %d / 自定义 key %d", key, key),
      character = key,
      hawaii = key,
      variantKey = key,
      characterRow = row,
      model = "custom",
    }},
  }
  S.customTargets[id] = S.customTarget
  updateStatus(string.format("CUSTOM TARGET READY key=%d row=%d; choose Apply", key, row))
  return true, S.customTarget
end

local function captureSnapshot()
  local snapshot = {
    pid = S.pid,
    characterBase = S.characterDb.base,
    costumeBase = S.costumeDb.base,
    identity = {},
    costume = {},
  }
  for _, sourceId in ipairs(allSourceIds()) do
    local source = sourceById(sourceId)
    for _, entry in ipairs(source.contextEntries) do
      local address = S.characterDb.mapping + entry.position * 4
      local value = readU32(address)
      if value == nil then
        return nil, string.format("could not back up identity source=%s key=%d",
          sourceId, entry.key)
      end
      snapshot.identity[#snapshot.identity + 1] = {
        sourceId = sourceId, key = entry.key, address = address, value = value,
      }
    end
    for _, row in ipairs(sortedRowsForSource(sourceId)) do
      local expected = source.records[row]
      local rowAddress = S.costumeDb.base + S.costumeDb.rowOffsets[row]
      local character = readU16(rowAddress + 0x04)
      local hawaii = readU16(rowAddress + 0x06)
      if character == nil or hawaii == nil then
        return nil, string.format("could not back up Costume source=%s row=%d",
          sourceId, row)
      end
      snapshot.costume[#snapshot.costume + 1] = {
        sourceId = sourceId,
        row = row,
        costume = expected.costume,
        characterAddress = rowAddress + 0x04,
        hawaiiAddress = rowAddress + 0x06,
        character = character,
        hawaii = hawaii,
      }
    end
  end
  if #snapshot.identity ~= 101 or #snapshot.costume ~= 128 then
    return nil, string.format("dual snapshot count mismatch identity=%d costume=%d",
      #snapshot.identity, #snapshot.costume)
  end
  return snapshot
end

local function selectedVariant(target, variantIndex)
  local index = tonumber(variantIndex)
  if not index or index < 1 or index > #(target.variants or {}) then return nil end
  return target.variants[index]
end

local function expectedPair(target, sourceId, row, outfitMode, variantIndex)
  if target.fixedNpc then
    return target.standardCharacter, target.standardHawaii
  end
  if outfitMode == "default_only" then
    return target.standardCharacter, target.standardHawaii
  elseif outfitMode == "fixed_variant" then
    local variant = selectedVariant(target, variantIndex)
    if not variant then return nil, nil end
    return fixedVariantPair(variant)
  end
  local sourcePlan = target.sourcePlans and target.sourcePlans[sourceId]
  local expected = sourcePlan and sourcePlan.records and sourcePlan.records[row]
  if not expected then return nil, nil end
  return expected.targetCharacter, expected.targetHawaii
end

local function backupIdentityValue(sourceId, key)
  if not S.backup then return nil end
  for _, item in ipairs(S.backup.identity) do
    if item.sourceId == sourceId and item.key == key then return item.value end
  end
  return nil
end

local function backupCostumeValue(sourceId, row)
  if not S.backup then return nil, nil end
  for _, item in ipairs(S.backup.costume) do
    if item.sourceId == sourceId and item.row == row then
      return item.character, item.hawaii
    end
  end
  return nil, nil
end

local function slotSelection(selection, sourceId)
  if type(selection) ~= "table" then return nil end
  if type(selection.slots) == "table" then return selection.slots[sourceId] end
  -- Compatibility with the v1.1 single-target API.
  if sourceIsSelected(sourceId, selection.sourceMode) then
    return {
      targetId = selection.targetId,
      mode = selection.mode,
      variantIndex = selection.variantIndex,
    }
  end
  return nil
end

local function expectedIdentity(selection, sourceId, entry)
  local slot = slotSelection(selection, sourceId)
  if not slot then return backupIdentityValue(sourceId, entry.key) end
  local target = targetById(slot.targetId)
  if not target then return nil end
  if slot.mode == "fixed_variant" then
    local variant = selectedVariant(target, slot.variantIndex)
    return variant and variant.characterRow or nil
  end
  return target.targetRow
end

local function expectedCostume(selection, sourceId, row)
  local slot = slotSelection(selection, sourceId)
  if not slot then return backupCostumeValue(sourceId, row) end
  local target = targetById(slot.targetId)
  if not target then return nil, nil end
  return expectedPair(target, sourceId, row, slot.mode, slot.variantIndex)
end

local function verifySelection(selection)
  for _, sourceId in ipairs(allSourceIds()) do
    local source = sourceById(sourceId)
    for _, entry in ipairs(source.contextEntries) do
      local expected = expectedIdentity(selection, sourceId, entry)
      local actual = readU32(S.characterDb.mapping + entry.position * 4)
      if expected == nil or actual ~= expected then
        return false, string.format(
          "identity verification failed source=%s key=%d expected=%s actual=%s",
          sourceId, entry.key, tostring(expected), tostring(actual))
      end
    end
    for _, row in ipairs(sortedRowsForSource(sourceId)) do
      local expectedCharacter, expectedHawaii = expectedCostume(selection, sourceId, row)
      if expectedCharacter == nil or expectedHawaii == nil then
        return false, string.format("missing expected Costume pair source=%s row=%d",
          sourceId, row)
      end
      local rowAddress = S.costumeDb.base + S.costumeDb.rowOffsets[row]
      local character = readU16(rowAddress + 0x04)
      local hawaii = readU16(rowAddress + 0x06)
      if character ~= expectedCharacter or hawaii ~= expectedHawaii then
        return false, string.format(
          "Costume verification failed source=%s row=%d expected=%d,%d actual=%s,%s",
          sourceId, row, expectedCharacter, expectedHawaii,
          tostring(character), tostring(hawaii))
      end
    end
  end
  return true
end

local function validateBackupBases(backup)
  if currentPid() ~= backup.pid then return false, "game process changed" end
  local okCharacter, characterOrError = validateCharacterDb(backup.characterBase)
  if not okCharacter then return false, "Character DB revalidation failed: " .. tostring(characterOrError) end
  local okCostume, costumeOrError = validateCostumeDb(backup.costumeBase)
  if not okCostume then return false, "Costume DB revalidation failed: " .. tostring(costumeOrError) end
  if characterOrError.mapping ~= S.characterDb.mapping or
     costumeOrError.rowOffsetTable ~= S.costumeDb.rowOffsetTable then
    return false, "validated runtime table layout changed"
  end
  S.characterDb = characterOrError
  S.costumeDb = costumeOrError
  return true
end

local function restoreSnapshot(snapshot)
  local okBases, baseError = validateBackupBases(snapshot)
  if not okBases then return false, baseError end

  for _, item in ipairs(snapshot.costume) do
    if not writeU16(item.characterAddress, item.character) then
      return false, "restore write failed Costume row " .. tostring(item.row) .. " character"
    end
    if not writeU16(item.hawaiiAddress, item.hawaii) then
      return false, "restore write failed Costume row " .. tostring(item.row) .. " hawaii"
    end
  end
  for _, item in ipairs(snapshot.identity) do
    if not writeU32(item.address, item.value) then
      return false, "restore write failed identity key " .. tostring(item.key)
    end
  end

  for _, item in ipairs(snapshot.costume) do
    local character = readU16(item.characterAddress)
    local hawaii = readU16(item.hawaiiAddress)
    if character ~= item.character or hawaii ~= item.hawaii then
      return false, string.format("restore verification failed Costume row=%d", item.row)
    end
  end
  for _, item in ipairs(snapshot.identity) do
    if readU32(item.address) ~= item.value then
      return false, "restore verification failed identity key " .. tostring(item.key)
    end
  end
  return true
end

local function writeSelection(selection)
  for _, sourceId in ipairs(allSourceIds()) do
    for _, row in ipairs(sortedRowsForSource(sourceId)) do
      local expectedCharacter, expectedHawaii = expectedCostume(selection, sourceId, row)
      if expectedCharacter == nil or expectedHawaii == nil then
        return false, string.format("missing selected Costume pair source=%s row=%d",
          sourceId, row)
      end
      local rowAddress = S.costumeDb.base + S.costumeDb.rowOffsets[row]
      if not writeU16(rowAddress + 0x04, expectedCharacter) then
        return false, string.format("target write failed Costume source=%s row=%d character",
          sourceId, row)
      end
      if not writeU16(rowAddress + 0x06, expectedHawaii) then
        return false, string.format("target write failed Costume source=%s row=%d hawaii",
          sourceId, row)
      end
    end
  end
  for _, sourceId in ipairs(allSourceIds()) do
    local source = sourceById(sourceId)
    for _, entry in ipairs(source.contextEntries) do
      local expected = expectedIdentity(selection, sourceId, entry)
      if expected == nil then
        return false, string.format("missing identity backup source=%s key=%d",
          sourceId, entry.key)
      end
      if not writeU32(S.characterDb.mapping + entry.position * 4, expected) then
        return false, string.format("target write failed identity source=%s key=%d",
          sourceId, entry.key)
      end
    end
  end
  return verifySelection(selection)
end

local function verifyVanilla()
  for _, sourceId in ipairs(allSourceIds()) do
    local source = sourceById(sourceId)
    for _, entry in ipairs(source.contextEntries) do
      local actual = readU32(S.characterDb.mapping + entry.position * 4)
      if actual ~= entry.originalRow then
        return false, string.format(
          "vanilla identity verification failed source=%s key=%d expected=%d actual=%s",
          sourceId, entry.key, entry.originalRow, tostring(actual))
      end
    end
    for _, row in ipairs(sortedRowsForSource(sourceId)) do
      local expected = source.records[row]
      local rowAddress = S.costumeDb.base + S.costumeDb.rowOffsets[row]
      local character = readU16(rowAddress + 0x04)
      local hawaii = readU16(rowAddress + 0x06)
      if character ~= expected.originalCharacter or hawaii ~= expected.originalHawaii then
        return false, string.format(
          "vanilla Costume verification failed source=%s row=%d expected=%d,%d actual=%s,%s",
          sourceId, row, expected.originalCharacter, expected.originalHawaii,
          tostring(character), tostring(hawaii))
      end
    end
  end
  return true
end

local function writeVanilla()
  for _, sourceId in ipairs(allSourceIds()) do
    local source = sourceById(sourceId)
    for _, row in ipairs(sortedRowsForSource(sourceId)) do
      local expected = source.records[row]
      local rowAddress = S.costumeDb.base + S.costumeDb.rowOffsets[row]
      if not writeU16(rowAddress + 0x04, expected.originalCharacter) then
        return false, string.format("vanilla reset failed Costume source=%s row=%d character",
          sourceId, row)
      end
      if not writeU16(rowAddress + 0x06, expected.originalHawaii) then
        return false, string.format("vanilla reset failed Costume source=%s row=%d hawaii",
          sourceId, row)
      end
    end
  end
  for _, sourceId in ipairs(allSourceIds()) do
    local source = sourceById(sourceId)
    for _, entry in ipairs(source.contextEntries) do
      if not writeU32(S.characterDb.mapping + entry.position * 4, entry.originalRow) then
        return false, string.format("vanilla reset failed identity source=%s key=%d",
          sourceId, entry.key)
      end
    end
  end
  return verifyVanilla()
end

function S.forceResetToVanilla(reason)
  local okLocate, locateError = S.validateAll()
  if not okLocate then return false, locateError end
  local rollback, snapshotError = captureSnapshot()
  if not rollback then return false, snapshotError end

  local okWrite, writeError = writeVanilla()
  if not okWrite then
    local okRollback, rollbackError = restoreSnapshot(rollback)
    if okRollback then
      updateStatus("ERROR, emergency reset rolled back: " .. tostring(writeError))
      return false, tostring(writeError) .. "; pre-reset state restored"
    end
    updateStatus("CRITICAL: emergency reset and rollback both failed: " ..
      tostring(rollbackError))
    return false, tostring(writeError) .. "; rollback failed: " .. tostring(rollbackError)
  end

  appendLog(string.format(
    "EMERGENCY_VANILLA_RESET reason=%s identity=%d costume_rows=%d verified=true",
    tostring(reason), #rollback.identity, #rollback.costume))
  S.backup = nil
  S.active = false
  S.activeToken = nil
  S.outfitMode = nil
  S.sourceMode = nil
  S.selection = nil
  updateStatus("RESET COMPLETE; vanilla Ichiban + Kiryu (101 mappings + 128 Costume rows) restored and verified")
  return true
end

local function outfitLabel(selection, target)
  if selection.mode == "context_matched" then return "Context Matched" end
  if selection.mode == "default_only" then return "Default Only" end
  local variant = selectedVariant(target, selection.variantIndex)
  local key = variant and select(1, fixedVariantPair(variant)) or nil
  return "Fixed Variant: " .. (variant and variant.label or "invalid") ..
    " | forced " .. tostring(key) .. "/" .. tostring(key)
end

local function validateSlot(sourceId, slot)
  if type(slot) ~= "table" then return false, "missing slot " .. tostring(sourceId) end
  local target = targetById(slot.targetId)
  if not target then return false, "unknown target " .. tostring(slot.targetId) end
  if slot.mode ~= "context_matched" and slot.mode ~= "default_only" and
     slot.mode ~= "fixed_variant" then
    return false, "unsupported Outfit Mode " .. tostring(slot.mode)
  end
  if slot.mode == "fixed_variant" then
    local variant = selectedVariant(target, slot.variantIndex)
    if not variant then return false, "invalid fixed variant " .. tostring(slot.variantIndex) end
    if not variant.characterRow then
      return false, "fixed variant has no Character Row " .. tostring(slot.variantIndex)
    end
  end
  return true, target
end

function S.applySlots(slots)
  if type(PLAN) ~= "table" or PLAN.schema ~= "y8.runtime_dual_source_selector.v2" then
    return false, "missing/invalid dual-source selector plan"
  end
  local selection = { slots = {} }
  local selectedCount = 0
  for _, sourceId in ipairs(allSourceIds()) do
    local slot = type(slots) == "table" and slots[sourceId] or nil
    if slot and slot.include ~= false then
      local normalized = {
        targetId = slot.targetId,
        mode = slot.mode,
        variantIndex = slot.mode == "fixed_variant" and tonumber(slot.variantIndex) or nil,
      }
      local okSlot, slotError = validateSlot(sourceId, normalized)
      if not okSlot then return false, slotError end
      selection.slots[sourceId] = normalized
      selectedCount = selectedCount + 1
    end
  end
  if selectedCount == 0 then return false, "select at least one protagonist slot" end

  local rollbackSnapshot
  local priorSelection = S.selection
  local wasActive = S.active
  if not wasActive then
    local okLocate, locateError = S.validateAll()
    if not okLocate then return false, locateError end
    if not S.costumeDb.transactionSafe then
      local states = {}
      for _, sourceId in ipairs(allSourceIds()) do
        states[#states + 1] = sourceId .. "=" .. tostring(S.costumeDb.sources[sourceId].state)
      end
      local errorText = "refusing first write: Costume states are " .. table.concat(states, ", ")
      updateStatus("ERROR: " .. errorText)
      return false, errorText
    end
    local backup, backupError = captureSnapshot()
    if not backup then
      updateStatus("ERROR: " .. tostring(backupError))
      return false, backupError
    end
    S.backup = backup
    rollbackSnapshot = backup
    appendLog(string.format(
      "BACKUP pid=%d identity=%d costume_rows=%d dual_source=true",
      backup.pid, #backup.identity, #backup.costume))
  else
    local okBases, baseError = validateBackupBases(S.backup)
    if not okBases then return false, baseError end
    local okCurrent, currentError = verifySelection(S.selection)
    if not okCurrent then
      local errorText = "refusing switch: active state changed externally: " .. tostring(currentError)
      updateStatus("ERROR: " .. errorText)
      return false, errorText
    end
    local snapshot, snapshotError = captureSnapshot()
    if not snapshot then return false, snapshotError end
    rollbackSnapshot = snapshot
  end

  local okWrite, writeError = writeSelection(selection)
  if not okWrite then
    local okRollback, rollbackError = restoreSnapshot(rollbackSnapshot)
    if okRollback then
      if not wasActive then
        S.backup = nil
        S.active = false
        S.selection = nil
      else
        S.active = true
        S.selection = priorSelection
      end
      updateStatus("ERROR, pre-switch rollback verified: " .. tostring(writeError))
      return false, tostring(writeError) .. "; pre-switch rollback verified"
    end
    S.active = true
    S.activeToken = "dual_source_selector"
    S.outfitMode = "recovery_required"
    updateStatus("CRITICAL: write failed and rollback failed: " .. tostring(rollbackError))
    return false, tostring(writeError) .. "; rollback failed: " .. tostring(rollbackError)
  end

  S.active = true
  S.activeToken = "dual_source_selector"
  S.outfitMode = "independent_slots"
  S.sourceMode = "independent"
  S.selection = selection
  local summaries = {}
  for _, sourceId in ipairs(allSourceIds()) do
    local slot = selection.slots[sourceId]
    if slot then
      local target = targetById(slot.targetId)
      summaries[#summaries + 1] = sourceId .. " -> " .. target.label ..
        " / " .. outfitLabel(slot, target)
      appendLog(string.format(
        "APPLY_SLOT source=%s target=%s base_row=%d identity_row=%d outfit_mode=%s variant=%s",
        sourceId, slot.targetId, target.targetRow,
        slot.mode == "fixed_variant" and selectedVariant(target, slot.variantIndex).characterRow
          or target.targetRow,
        slot.mode, tostring(slot.variantIndex)))
    else
      summaries[#summaries + 1] = sourceId .. " -> first backup"
    end
  end
  updateStatus(string.format(
    "APPLIED / 已应用：%s | verified / 已验证 | reopen menu; reload or change maps for free roam",
    table.concat(summaries, " | ")))
  appendLog(string.format(
    "APPLY independent_slots=%d identity=101 costume_rows=128 verified=true", selectedCount))
  return true
end

-- Backward-compatible API used by older scripts and address-list entries.
function S.apply(sourceMode, targetId, outfitMode, variantIndex)
  if #sourceIdsForMode(sourceMode) == 0 then
    return false, "unsupported Source Player " .. tostring(sourceMode)
  end
  local slots = {}
  for _, sourceId in ipairs(sourceIdsForMode(sourceMode)) do
    slots[sourceId] = {
      include = true,
      targetId = targetId,
      mode = outfitMode,
      variantIndex = variantIndex,
    }
  end
  return S.applySlots(slots)
end

function S.restore(reason)
  if not S.backup then
    S.active = false
    S.activeToken = nil
    S.outfitMode = nil
    S.sourceMode = nil
    S.selection = nil
    return true
  end
  if currentPid() ~= S.backup.pid then
    appendLog(string.format("RESTORE_SKIPPED old_pid=%s new_pid=%s reason=%s",
      tostring(S.backup.pid), tostring(currentPid()), tostring(reason)))
    S.backup = nil
    S.active = false
    S.activeToken = nil
    S.outfitMode = nil
    S.sourceMode = nil
    S.selection = nil
    S.characterDb = nil
    S.costumeDb = nil
    updateStatus("inactive; old game process ended, no stale write attempted")
    return true
  end

  local okRestore, restoreError = restoreSnapshot(S.backup)
  if not okRestore then
    updateStatus("CRITICAL: restore failed: " .. tostring(restoreError))
    return false, restoreError
  end
  appendLog(string.format("RESTORE reason=%s identity=%d costume_rows=%d verified=true",
    tostring(reason), #S.backup.identity, #S.backup.costume))
  S.backup = nil
  S.active = false
  S.activeToken = nil
  S.outfitMode = nil
  S.sourceMode = nil
  S.selection = nil
  updateStatus("RESTORED / 已恢复：the original runtime state for both protagonists was verified")
  return true
end

function S.disable(token)
  if not S.active then return true end
  if token and S.activeToken and token ~= S.activeToken then return true end
  return S.restore("Disable " .. tostring(token or S.activeToken))
end

local function addComboItem(combo, text)
  if combo and combo.Items and type(combo.Items.add) == "function" then
    combo.Items.add(text)
  end
end

local function clearCombo(combo)
  if combo and combo.Items and type(combo.Items.clear) == "function" then
    combo.Items.clear()
  end
end

local function selectedTargetId()
  local controls = S.controls
  if not controls then return nil end
  local index = (tonumber(controls.character.ItemIndex) or -1) + 1
  local catalogIndex = controls.catalog and tonumber(controls.catalog.ItemIndex) or 0
  if catalogIndex == 3 then
    return S.customTarget and S.customTarget.id or nil
  end
  return S.visibleTargetIds[index]
end

local function selectedSourceMode()
  local controls = S.controls
  if not controls or not controls.source then return nil end
  local index = tonumber(controls.source.ItemIndex) or -1
  if index == 0 then return "ichiban" end
  if index == 1 then return "kiryu" end
  if index == 2 then return "both" end
  return nil
end

local function selectedMode()
  local controls = S.controls
  if not controls then return nil end
  local index = tonumber(controls.mode.ItemIndex) or -1
  if index == 0 then return "context_matched" end
  if index == 1 then return "default_only" end
  if index == 2 then return "fixed_variant" end
  return nil
end

local function refreshVariants()
  local controls = S.controls
  if not controls then return end
  clearCombo(controls.variant)
  local target = targetById(selectedTargetId())
  if target then
    for _, variant in ipairs(target.variants or {}) do
      addComboItem(controls.variant, variant.label)
    end
  end
  controls.variant.ItemIndex = 0
  controls.variant.Enabled = selectedMode() == "fixed_variant"
end

local function refreshTargetList()
  local controls = S.controls
  if not controls or not controls.character then return end
  clearCombo(controls.character)
  local catalogIndex = controls.catalog and tonumber(controls.catalog.ItemIndex) or 0
  local query = controls.search and string.lower(tostring(controls.search.Text or "")) or ""
  S.visibleTargetIds = {}
  if catalogIndex == 3 then
    if S.customTarget then
      addComboItem(controls.character, S.customTarget.label)
      controls.character.ItemIndex = 0
    else
      addComboItem(controls.character, "Enter a Character key below / 请在下方输入 key")
      controls.character.ItemIndex = 0
    end
  else
    local order = PLAN.targetOrder or {}
    local targets = PLAN.targets or {}
    if catalogIndex == 1 then order, targets = PLAN.labTargetOrder or {}, PLAN.labTargets or {} end
    if catalogIndex == 2 then order, targets = PLAN.maleTargetOrder or {}, PLAN.maleTargets or {} end
    for _, targetId in ipairs(order) do
      local target = targets[targetId]
      local label = target and target.label or targetId
      if query == "" or string.find(string.lower(label), query, 1, true) then
        S.visibleTargetIds[#S.visibleTargetIds + 1] = targetId
        addComboItem(controls.character, label)
      end
    end
    controls.character.ItemIndex = #S.visibleTargetIds > 0 and 0 or -1
  end
  refreshVariants()
end

local function makeLabel(form, caption, left, top, width)
  local label = createLabel(form)
  label.Parent = form
  label.Caption = caption
  label.Left = left
  label.Top = top
  label.Width = width
  return label
end

function S.showSelector()
  if S.form then
    pcall(function() S.form.show() end)
    pcall(function() S.form.bringToFront() end)
    return true
  end
  if type(createForm) ~= "function" or type(createComboBox) ~= "function" then
    return false, "this Cheat Engine build has no Lua form support"
  end

  local form = createForm(false)
  form.Caption = "Yakuza 8 Runtime Character + Costume + NPC Selector v0.6.1"
  form.Width = 720
  form.Height = 350
  form.Position = "poScreenCenter"

  makeLabel(form, "Character / 角色", 18, 18, 150)
  local character = createComboBox(form)
  character.Parent = form
  character.Left = 170
  character.Top = 14
  character.Width = 520
  character.Style = "csDropDownList"
  for _, targetId in ipairs(PLAN.targetOrder) do
    addComboItem(character, PLAN.targets[targetId].label)
  end
  character.ItemIndex = 8 -- Chitose: proven Phase 1.5 default

  makeLabel(form, "Outfit Mode / 服装模式", 18, 58, 150)
  local mode = createComboBox(form)
  mode.Parent = form
  mode.Left = 170
  mode.Top = 54
  mode.Width = 520
  mode.Style = "csDropDownList"
  addComboItem(mode, "Context Matched / 随场景匹配")
  addComboItem(mode, "Default Only / 全部默认服装")
  addComboItem(mode, "Fixed Variant / 固定指定服装")
  mode.ItemIndex = 0

  makeLabel(form, "Fixed Variant / 指定服装", 18, 98, 150)
  local variant = createComboBox(form)
  variant.Parent = form
  variant.Left = 170
  variant.Top = 94
  variant.Width = 520
  variant.Style = "csDropDownList"

  local applyButton = createButton(form)
  applyButton.Parent = form
  applyButton.Caption = "Apply / 应用"
  applyButton.Left = 170
  applyButton.Top = 140
  applyButton.Width = 250
  applyButton.Height = 34

  local restoreButton = createButton(form)
  restoreButton.Parent = form
  restoreButton.Caption = "Restore Original / 恢复初始状态"
  restoreButton.Left = 440
  restoreButton.Top = 140
  restoreButton.Width = 250
  restoreButton.Height = 34

  local resetButton = createButton(form)
  resetButton.Parent = form
  resetButton.Caption = "EMERGENCY: Reset Ichiban Source to VANILLA"
  resetButton.Left = 170
  resetButton.Top = 184
  resetButton.Width = 520
  resetButton.Height = 34

  local status = makeLabel(form,
    "Choose a character and outfit, then Apply.", 18, 232, 672)
  status.AutoSize = false
  status.Height = 62
  status.WordWrap = true

  S.form = form
  S.controls = {
    character = character, mode = mode, variant = variant, status = status,
  }

  character.OnChange = refreshVariants
  mode.OnChange = refreshVariants
  applyButton.OnClick = function()
    local targetId = selectedTargetId()
    local outfitMode = selectedMode()
    local variantIndex = (tonumber(variant.ItemIndex) or -1) + 1
    local ok, err = S.apply(targetId, outfitMode, variantIndex)
    if not ok then updateStatus("ERROR: " .. tostring(err)) end
  end
  restoreButton.OnClick = function()
    local ok, err = S.restore("Selector Restore button")
    if not ok then updateStatus("ERROR: " .. tostring(err)) end
  end
  resetButton.OnClick = function()
    local ok, err = S.forceResetToVanilla("Selector emergency reset button")
    if not ok then updateStatus("ERROR: " .. tostring(err)) end
  end
  form.OnClose = function()
    S.form = nil
    S.controls = nil
  end

  refreshVariants()
  form.show()
  updateStatus("selector ready; first Apply saves the original state")
  return true
end

-- Override the inherited Phase 1.5 form with the Phase 1.7 dual-source UI.
function S.showSelector()
  if S.form then
    pcall(function() S.form.show() end)
    pcall(function() S.form.bringToFront() end)
    return true
  end
  if type(createForm) ~= "function" or type(createComboBox) ~= "function" then
    return false, "this Cheat Engine build has no Lua form support"
  end

  local form = createForm(false)
  form.Caption = "Yakuza 8 Dual-Protagonist Character + Costume Selector v0.2.0"
  form.Width = 720
  form.Height = 400
  form.Position = "poScreenCenter"

  makeLabel(form, "Source Player / 源主角", 18, 18, 150)
  local source = createComboBox(form)
  source.Parent = form
  source.Left = 170
  source.Top = 14
  source.Width = 520
  source.Style = "csDropDownList"
  addComboItem(source, "Ichiban / 春日")
  addComboItem(source, "Kiryu / 桐生")
  addComboItem(source, "Both Protagonists / 双主角")
  source.ItemIndex = 0

  makeLabel(form, "Character / 角色", 18, 58, 150)
  local character = createComboBox(form)
  character.Parent = form
  character.Left = 170
  character.Top = 54
  character.Width = 520
  character.Style = "csDropDownList"
  for _, targetId in ipairs(PLAN.targetOrder) do
    addComboItem(character, PLAN.targets[targetId].label)
  end
  character.ItemIndex = 8 -- Chitose remains the proven default test target.

  makeLabel(form, "Outfit Mode / 服装模式", 18, 98, 150)
  local mode = createComboBox(form)
  mode.Parent = form
  mode.Left = 170
  mode.Top = 94
  mode.Width = 520
  mode.Style = "csDropDownList"
  addComboItem(mode, "Context Matched / 随场景匹配")
  addComboItem(mode, "Default Only / 全部标准默认服装")
  addComboItem(mode, "Fixed Variant / 固定指定服装")
  mode.ItemIndex = 0

  makeLabel(form, "Fixed Variant / 指定服装", 18, 138, 150)
  local variant = createComboBox(form)
  variant.Parent = form
  variant.Left = 170
  variant.Top = 134
  variant.Width = 520
  variant.Style = "csDropDownList"

  local applyButton = createButton(form)
  applyButton.Parent = form
  applyButton.Caption = "Apply / 应用"
  applyButton.Left = 170
  applyButton.Top = 180
  applyButton.Width = 250
  applyButton.Height = 34

  local restoreButton = createButton(form)
  restoreButton.Parent = form
  restoreButton.Caption = "Restore First Backup / 恢复首次备份"
  restoreButton.Left = 440
  restoreButton.Top = 180
  restoreButton.Width = 250
  restoreButton.Height = 34

  local resetButton = createButton(form)
  resetButton.Parent = form
  resetButton.Caption = "EMERGENCY: Reset BOTH Sources to VANILLA"
  resetButton.Left = 170
  resetButton.Top = 224
  resetButton.Width = 520
  resetButton.Height = 34

  local status = makeLabel(form,
    "Choose source player, character, and outfit, then Apply.", 18, 272, 672)
  status.AutoSize = false
  status.Height = 68
  status.WordWrap = true

  S.form = form
  S.controls = {
    source = source,
    character = character,
    mode = mode,
    variant = variant,
    status = status,
  }

  character.OnChange = refreshVariants
  mode.OnChange = refreshVariants
  applyButton.OnClick = function()
    local targetId = selectedTargetId()
    local outfitMode = selectedMode()
    local variantIndex = (tonumber(variant.ItemIndex) or -1) + 1
    local ok, err = S.apply(selectedSourceMode(), targetId, outfitMode, variantIndex)
    if not ok then updateStatus("ERROR: " .. tostring(err)) end
  end
  restoreButton.OnClick = function()
    local ok, err = S.restore("Dual-source selector Restore button")
    if not ok then updateStatus("ERROR: " .. tostring(err)) end
  end
  resetButton.OnClick = function()
    local ok, err = S.forceResetToVanilla("Dual-source selector emergency reset button")
    if not ok then updateStatus("ERROR: " .. tostring(err)) end
  end
  form.OnClose = function()
    S.form = nil
    S.controls = nil
  end

  refreshVariants()
  form.show()
  updateStatus("selector ready; first Apply saves both source states")
  return true
end

-- Release UI: curated targets, female/male NPC catalogs, search, and custom key.
function S.showSelector()
  if S.form then
    pcall(function() S.form.show() end)
    pcall(function() S.form.bringToFront() end)
    return true
  end
  if type(createForm) ~= "function" or type(createComboBox) ~= "function" or
     type(createEdit) ~= "function" then
    return false, "this Cheat Engine build has no required Lua form support"
  end

  local form = createForm(false)
  form.Caption = "Yakuza 8 Character & Costume Selector v1.1.1-rc1"
  form.Width = 900
  form.Height = 610
  form.Position = "poScreenCenter"

  makeLabel(form, "Replace / 替换对象", 18, 18, 170)
  local source = createComboBox(form)
  source.Parent = form
  source.Left = 190
  source.Top = 14
  source.Width = 680
  source.Style = "csDropDownList"
  addComboItem(source, "Ichiban only / 仅春日")
  addComboItem(source, "Kiryu only / 仅桐生")
  addComboItem(source, "Both protagonists / 春日与桐生")
  source.ItemIndex = 0

  makeLabel(form, "Character List / 角色列表", 18, 58, 170)
  local catalog = createComboBox(form)
  catalog.Parent = form
  catalog.Left = 190
  catalog.Top = 54
  catalog.Width = 680
  catalog.Style = "csDropDownList"
  addComboItem(catalog, "Recommended & verified / 推荐与已确认 (" .. tostring(#(PLAN.targetOrder or {})) .. ")")
  addComboItem(catalog, "Advanced: Unverified female NPCs / 高级：未确认女性 NPC (" ..
    tostring(#(PLAN.labTargetOrder or {})) .. ")")
  addComboItem(catalog, "Advanced: Male NPC Lab / 高级：男性 NPC 目录 (" ..
    tostring(#(PLAN.maleTargetOrder or {})) .. ")")
  addComboItem(catalog, "Advanced: Custom Character key / 高级：自定义角色 key")
  catalog.ItemIndex = 0

  makeLabel(form, "Character / 角色", 18, 98, 170)
  local character = createComboBox(form)
  character.Parent = form
  character.Left = 190
  character.Top = 94
  character.Width = 680
  character.Style = "csDropDownList"

  makeLabel(form, "Search / 搜索", 18, 218, 170)
  local search = createEdit(form)
  search.Parent = form
  search.Left = 190
  search.Top = 214
  search.Width = 680
  search.Text = ""

  makeLabel(form, "Outfit Mode / 服装模式", 18, 138, 170)
  local mode = createComboBox(form)
  mode.Parent = form
  mode.Left = 190
  mode.Top = 134
  mode.Width = 680
  mode.Style = "csDropDownList"
  addComboItem(mode, "Context Matched (Recommended) / 场景匹配（推荐）")
  addComboItem(mode, "Default Outfit Everywhere / 始终默认服装")
  addComboItem(mode, "Fixed Outfit Variant / 固定指定服装")
  mode.ItemIndex = 0

  makeLabel(form, "Fixed Variant / 指定服装", 18, 178, 170)
  local variant = createComboBox(form)
  variant.Parent = form
  variant.Left = 190
  variant.Top = 174
  variant.Width = 680
  variant.Style = "csDropDownList"

  makeLabel(form, "Custom Key / 自定义 key", 18, 258, 170)
  local customKey = createEdit(form)
  customKey.Parent = form
  customKey.Left = 190
  customKey.Top = 254
  customKey.Width = 420
  customKey.Text = ""

  local customButton = createButton(form)
  customButton.Parent = form
  customButton.Caption = "Resolve Custom Key / 解析自定义 key"
  customButton.Left = 625
  customButton.Top = 252
  customButton.Width = 245
  customButton.Height = 28

  local applyButton = createButton(form)
  applyButton.Parent = form
  applyButton.Caption = "Apply Selection / 应用选择"
  applyButton.Left = 190
  applyButton.Top = 300
  applyButton.Width = 330
  applyButton.Height = 34

  local restoreButton = createButton(form)
  restoreButton.Parent = form
  restoreButton.Caption = "Restore Original State / 恢复初始状态"
  restoreButton.Left = 540
  restoreButton.Top = 300
  restoreButton.Width = 330
  restoreButton.Height = 34

  local resetButton = createButton(form)
  resetButton.Parent = form
  resetButton.Caption = "EMERGENCY ONLY: Force Vanilla Reset / 仅紧急使用：强制恢复原版"
  resetButton.Left = 190
  resetButton.Top = 346
  resetButton.Width = 680
  resetButton.Height = 34

  local note = makeLabel(form,
    "How it takes effect / 生效方式：Menu and party screens update after reopening. " ..
    "Free-roam models usually require loading a save or changing maps. Voice follows Character Identity.\n" ..
    "菜单与队伍界面重新打开即可刷新；自由探索通常需要读档或切换地图；语音随角色身份切换。",
    18, 392, 852)
  note.AutoSize = false
  note.Height = 62
  note.WordWrap = true

  local safety = makeLabel(form,
    "Safety / 安全提示：Use Restore Original State before closing CE or quitting the game. " ..
    "Emergency Vanilla Reset ignores the saved backup and may overwrite active file-Mod database values.\n" ..
    "关闭 CE 或退出游戏前请先恢复初始状态。紧急原版重置不会使用备份，并可能覆盖文件 Mod 的数据库值。",
    18, 460, 852)
  safety.AutoSize = false
  safety.Height = 66
  safety.WordWrap = true

  local status = makeLabel(form,
    "Ready / 就绪：Choose replacement target, character and outfit, then Apply Selection.", 18, 536, 852)
  status.AutoSize = false
  status.Height = 70
  status.WordWrap = true

  S.form = form
  S.controls = {
    source = source,
    catalog = catalog,
    character = character,
    mode = mode,
    variant = variant,
    customKey = customKey,
    search = search,
    status = status,
  }

  catalog.OnChange = refreshTargetList
  search.OnChange = refreshTargetList
  character.OnChange = refreshVariants
  mode.OnChange = refreshVariants
  customButton.OnClick = function()
    local ok, result = S.prepareCustomTarget(customKey.Text)
    if not ok then
      updateStatus("ERROR: " .. tostring(result))
      return
    end
    catalog.ItemIndex = 3
    refreshTargetList()
  end
  applyButton.OnClick = function()
    local targetId = selectedTargetId()
    local outfitMode = selectedMode()
    local variantIndex = (tonumber(variant.ItemIndex) or -1) + 1
    local ok, err = S.apply(selectedSourceMode(), targetId, outfitMode, variantIndex)
    if not ok then updateStatus("ERROR: " .. tostring(err)) end
  end
  restoreButton.OnClick = function()
    local ok, err = S.restore("Character Selector Restore button")
    if not ok then updateStatus("ERROR: " .. tostring(err)) end
  end
  resetButton.OnClick = function()
    local ok, err = S.forceResetToVanilla("Character Selector emergency reset button")
    if not ok then updateStatus("ERROR: " .. tostring(err)) end
  end
  form.OnClose = function()
    S.form = nil
    S.controls = nil
  end

  refreshTargetList()
  form.show()
  updateStatus("READY v" .. SCRIPT_VERSION ..
    "; first Apply safely saves the original runtime state for both protagonists")
  return true
end

-- v1.2 release UI: one editor with two persistent, independently applied slots.
local UI_TEXT = {
  title = { en="Like a Dragon: Infinite Wealth — Character Studio v1.3.0-rc1",
            zh="如龙8 无尽财富 · 角色模型工坊 v1.3.0-rc1" },
  editSlot = { en="Edit protagonist", zh="编辑主角槽位" },
  ichiban = { en="Ichiban", zh="春日" },
  kiryu = { en="Kiryu", zh="桐生" },
  include = { en="Include this slot in Apply", zh="参与本次应用" },
  catalog = { en="Character list", zh="角色列表" },
  character = { en="Character", zh="角色" },
  search = { en="Search", zh="搜索" },
  outfitMode = { en="Outfit behavior", zh="服装行为" },
  variant = { en="Fixed outfit", zh="指定服装" },
  customKey = { en="Custom Character key", zh="自定义 Character key" },
  resolve = { en="Resolve key", zh="解析 key" },
  apply = { en="Apply independent slots", zh="应用双主角独立设置" },
  restore = { en="Restore first backup", zh="恢复首次应用前状态" },
  reset = { en="EMERGENCY: Force vanilla reset", zh="仅紧急使用：强制恢复原版" },
  log = { en="Open diagnostic log", zh="打开诊断日志" },
  summary = { en="Current slot plan", zh="当前双槽位方案" },
  ready = { en="Choose each protagonist separately, then Apply.",
            zh="分别设置春日与桐生，然后一次性应用。" },
  note = { en="Menu screens refresh after reopening. Free roam may require loading a save or changing maps. Existing World Actors are not rebuilt in place.",
           zh="菜单重新打开即可刷新；自由探索可能需要读档或切图。已生成的 World Actor 不会原地重建。" },
  safety = { en="Restore the first backup before closing CE. The emergency reset ignores the backup and can overwrite file-Mod database values.",
             zh="关闭 CE 前请恢复首次备份。紧急重置不使用备份，可能覆盖文件 Mod 的数据库值。" },
  defaultOutfit = { en="Default outfit", zh="默认服装" },
}

local CATALOG_TEXT = {
  { en="Recommended & verified", zh="推荐与已确认" },
  { en="Advanced: unverified female NPCs", zh="高级：未确认女性 NPC" },
  { en="Advanced: male NPC lab", zh="高级：男性 NPC 目录" },
  { en="Advanced: custom Character key", zh="高级：自定义 Character key" },
}

local MODE_IDS = { "context_matched", "default_only", "fixed_variant" }
local MODE_TEXT = {
  { en="Context matched (recommended)", zh="随场景匹配（推荐）" },
  { en="Default outfit everywhere", zh="始终使用默认服装" },
  { en="Fixed outfit variant", zh="固定指定服装" },
}

local COSTUME_GROUPS = {
  host={en="Host",zh="男公关"}, dancer={en="Breaker",zh="街舞者"},
  cook={en="Chef",zh="厨师"}, idol={en="Idol",zh="偶像"},
  queen={en="Night Queen",zh="夜之女王"}, kunoichi={en="Kunoichi",zh="女忍者"},
  samurai={en="Samurai",zh="武士"}, actionstar={en="Action Star",zh="动作巨星"},
  marine={en="Aquanaut",zh="海洋潜水员"}, footballer={en="Linebacker",zh="橄榄球员"},
  western={en="Desperado",zh="西部枪手"}, firedancer={en="Pyrodancer",zh="火焰舞者"},
  housekeeper={en="Housekeeper",zh="家政管家"}, tropicaldancer={en="Geodancer",zh="热带舞者"},
  tennis={en="Tennis Ace",zh="网球高手"},
}

local COSTUME_NAMES_ZH = {
  ["Normal"]="标准款", ["Pattern A"]="配色 A", ["Pattern B"]="配色 B",
  ["Normal Swimsuit"]="标准泳装", ["Hawaii Outfit"]="夏威夷常服",
  ["Yokohama Outfit"]="横滨常服",
}

local SPECIAL_NAMES_ZH = {
  ["Hello Worker"]="职介所员工装", ["Casino Attire"]="赌场服",
  ["Waitress Attire"]="女服务员装", ["Goro Majima"]="真岛吾朗套装",
  ["Taiga Saejima"]="冴岛大河套装", ["Shun Akiyama"]="秋山骏套装",
  ["Makoto Date"]="伊达真套装", ["Ryuji Goda"]="乡田龙司套装",
  ["Kaoru Sayama"]="狭山薰套装", ["Ono Michio"]="小野道夫套装",
  ["Robo Michio"]="机器小野道夫套装", ["Gold Swimsuit"]="金色泳装",
  ["Traditional Swimsuit"]="传统泳装", ["Tasty Swimsuit"]="趣味泳装",
  ["Security Detail"]="安保人员装", ["Tech Inspector"]="技术检查员装",
  ["Dragon of Dojima"]="堂岛之龙", ["Resurrected Dragon"]="复活之龙套装",
  ["Hero"]="勇者套装", ["Hostess"]="女公关装",
}

local function uiText(key)
  local item = UI_TEXT[key]
  return item and (item[S.language] or item.en) or key
end

local function localizedDataLabel(text)
  text = tostring(text or "")
  local head, rest = text:match("^%[(.-)%]%s*(.*)$")
  if head then
    local enHead, zhHead = head:match("^(.-)%s*/%s*(.-)$")
    local localizedHead = S.language == "zh" and (zhHead or enHead) or enHead
    if rest ~= "" and not string.find(rest, " — ", 1, true) and
       not string.find(rest, " | ", 1, true) then
      local enRest, zhRest = rest:match("^(.-)%s*/%s*(.-)$")
      if enRest and zhRest then rest = S.language == "zh" and zhRest or enRest end
    end
    return "[" .. tostring(localizedHead or head) .. "] " .. rest
  end
  return text
end

local function costumeGroup(costumeKey)
  for prefix, labels in pairs(COSTUME_GROUPS) do
    if costumeKey == prefix or costumeKey:sub(1, #prefix + 1) == prefix .. "_" then
      return labels
    end
  end
  return nil
end

local function readableVariantLabel(variant)
  if not variant then return "" end
  local costumeId = tonumber(variant.sourceCostume)
  local name = tostring(variant.costumeName or "")
  local key = tostring(variant.costumeKey or "")
  if not costumeId or name == "" then
    if tostring(variant.label or ""):match("^Default%s*/") then return uiText("defaultOutfit") end
    return localizedDataLabel(variant.label)
  end
  local group = costumeGroup(key)
  if S.language == "en" then
    local readable = group and (group.en .. " · " .. name) or name
    return readable .. "  (costume " .. tostring(costumeId) .. ")"
  end
  local hair = ""
  if name:sub(-13) == " (Short Hair)" then
    name = name:sub(1, -14)
    hair = "（短发）"
  elseif string.find(key, "_amikomi", 1, true) then
    hair = "（编发）"
  end
  local readable
  if name:sub(1, 16) == "Special Outfit: " then
    local detail = name:sub(17)
    readable = "特别服装：" .. (SPECIAL_NAMES_ZH[detail] or detail) .. hair
  else
    readable = (COSTUME_NAMES_ZH[name] or name) .. hair
  end
  if group then readable = group.zh .. " · " .. readable end
  return readable .. "（服装 " .. tostring(costumeId) .. "）"
end

local function defaultSlotStates()
  if not S.slotStates.ichiban then
    S.slotStates.ichiban = {
      include=true, catalogIndex=0, query="", targetId="chitose", modeIndex=0,
      variantIndex=0, customTargetId=nil,
    }
  end
  if not S.slotStates.kiryu then
    S.slotStates.kiryu = {
      include=true, catalogIndex=0, query="", targetId="kiryu", modeIndex=0,
      variantIndex=0, customTargetId=nil,
    }
  end
end

local function currentSlotState()
  defaultSlotStates()
  return S.slotStates[S.editingSourceId]
end

local function currentEditorTargetId()
  local controls = S.controls
  if not controls or not controls.character then return nil end
  local index = (tonumber(controls.character.ItemIndex) or -1) + 1
  return S.visibleTargetIds[index]
end

local function updateSlotSummary()
  local controls = S.controls
  if not controls or not controls.summary then return end
  local parts = {}
  for _, sourceId in ipairs(allSourceIds()) do
    local state = S.slotStates[sourceId]
    local target = state and targetById(state.targetId) or nil
    local sourceName = uiText(sourceId)
    if not state or not state.include then
      parts[#parts + 1] = sourceName .. ": —"
    else
      local targetName = target and localizedDataLabel(target.label) or "?"
      local modeName = MODE_TEXT[(state.modeIndex or 0) + 1][S.language]
      parts[#parts + 1] = sourceName .. ": " .. targetName .. " · " .. modeName
    end
  end
  controls.summary.Caption = uiText("summary") .. "：" .. table.concat(parts, "    |    ")
end

local function refreshVariantsV12(preferredIndex)
  local controls = S.controls
  if not controls then return end
  clearCombo(controls.variant)
  local target = targetById(currentEditorTargetId())
  if target then
    for _, variant in ipairs(target.variants or {}) do
      addComboItem(controls.variant, readableVariantLabel(variant))
    end
  end
  local count = controls.variant.Items and tonumber(controls.variant.Items.Count) or 0
  local wanted = tonumber(preferredIndex) or 0
  if wanted < 0 or wanted >= count then wanted = 0 end
  controls.variant.ItemIndex = count > 0 and wanted or -1
  local fixed = (tonumber(controls.mode.ItemIndex) or 0) == 2
  controls.variant.Enabled = fixed
  local state = currentSlotState()
  state.variantIndex = tonumber(controls.variant.ItemIndex) or 0
end

local function refreshTargetListV12(preferredTargetId)
  local controls = S.controls
  if not controls then return end
  clearCombo(controls.character)
  local state = currentSlotState()
  local catalogIndex = tonumber(controls.catalog.ItemIndex) or 0
  local query = string.lower(tostring(controls.search.Text or ""))
  S.visibleTargetIds = {}
  if catalogIndex == 3 then
    local customId = state.customTargetId
    local target = customId and targetById(customId) or nil
    if target then
      S.visibleTargetIds[1] = customId
      addComboItem(controls.character, localizedDataLabel(target.label))
    else
      addComboItem(controls.character,
        S.language == "zh" and "请在下方输入 Character key" or "Enter a Character key below")
    end
  else
    local order, targets = PLAN.targetOrder or {}, PLAN.targets or {}
    if catalogIndex == 1 then order, targets = PLAN.labTargetOrder or {}, PLAN.labTargets or {} end
    if catalogIndex == 2 then order, targets = PLAN.maleTargetOrder or {}, PLAN.maleTargets or {} end
    for _, targetId in ipairs(order) do
      local target = targets[targetId]
      local raw = target and target.label or targetId
      if query == "" or string.find(string.lower(raw), query, 1, true) then
        S.visibleTargetIds[#S.visibleTargetIds + 1] = targetId
        addComboItem(controls.character, localizedDataLabel(raw))
      end
    end
  end
  local selected = -1
  for index, targetId in ipairs(S.visibleTargetIds) do
    if targetId == preferredTargetId then selected = index - 1 break end
  end
  if selected < 0 and #S.visibleTargetIds > 0 then selected = 0 end
  controls.character.ItemIndex = selected
  state.targetId = S.visibleTargetIds[selected + 1]
  local target = targetById(state.targetId)
  if target and target.fixedNpc then
    state.modeIndex = 2
    controls.mode.ItemIndex = 2
    controls.mode.Enabled = false
  else
    controls.mode.Enabled = true
  end
  refreshVariantsV12(state.variantIndex)
  updateSlotSummary()
end

local function saveEditorState()
  if S.uiLoading or not S.controls then return end
  local state = currentSlotState()
  state.include = S.controls.include.Checked == true
  state.catalogIndex = tonumber(S.controls.catalog.ItemIndex) or 0
  state.query = tostring(S.controls.search.Text or "")
  state.targetId = currentEditorTargetId() or state.targetId
  state.modeIndex = tonumber(S.controls.mode.ItemIndex) or 0
  state.variantIndex = tonumber(S.controls.variant.ItemIndex) or 0
  updateSlotSummary()
end

local function loadEditorState(sourceId)
  defaultSlotStates()
  S.uiLoading = true
  S.editingSourceId = sourceId
  local state = currentSlotState()
  local controls = S.controls
  controls.source.ItemIndex = sourceId == "kiryu" and 1 or 0
  controls.include.Checked = state.include ~= false
  controls.catalog.ItemIndex = state.catalogIndex or 0
  controls.search.Text = state.query or ""
  refreshTargetListV12(state.targetId)
  controls.mode.ItemIndex = state.modeIndex or 0
  refreshVariantsV12(state.variantIndex)
  S.uiLoading = false
  updateSlotSummary()
end

function S.showSelector()
  if S.form then
    pcall(function() S.form.show() end)
    pcall(function() S.form.bringToFront() end)
    return true
  end
  if type(createForm) ~= "function" or type(createComboBox) ~= "function" or
     type(createEdit) ~= "function" or type(createCheckBox) ~= "function" then
    return false, "this Cheat Engine build has no required Lua form support"
  end
  defaultSlotStates()
  local form = createForm(false)
  form.Caption = uiText("title")
  form.Width = 980
  form.Height = 720
  form.Position = "poScreenCenter"

  local function label(key, top)
    return makeLabel(form, uiText(key), 18, top, 188)
  end
  label("editSlot", 18)
  local source = createComboBox(form)
  source.Parent=form; source.Left=210; source.Top=14; source.Width=420; source.Style="csDropDownList"
  addComboItem(source, uiText("ichiban")); addComboItem(source, uiText("kiryu"))
  local languageButton = createButton(form)
  languageButton.Parent=form; languageButton.Left=820; languageButton.Top=12
  languageButton.Width=130; languageButton.Height=28
  languageButton.Caption = S.language == "zh" and "EN" or "中文"
  local include = createCheckBox(form)
  include.Parent=form; include.Left=650; include.Top=18; include.Width=160
  include.Caption=uiText("include")

  label("catalog", 58)
  local catalog=createComboBox(form)
  catalog.Parent=form; catalog.Left=210; catalog.Top=54; catalog.Width=740; catalog.Style="csDropDownList"
  for index, item in ipairs(CATALOG_TEXT) do
    local count = index == 1 and #(PLAN.targetOrder or {}) or
      (index == 2 and #(PLAN.labTargetOrder or {}) or
      (index == 3 and #(PLAN.maleTargetOrder or {}) or nil))
    addComboItem(catalog, item[S.language] .. (count and (" (" .. tostring(count) .. ")") or ""))
  end
  label("character", 98)
  local character=createComboBox(form)
  character.Parent=form; character.Left=210; character.Top=94; character.Width=740; character.Style="csDropDownList"
  label("search", 138)
  local search=createEdit(form)
  search.Parent=form; search.Left=210; search.Top=134; search.Width=740
  label("outfitMode", 178)
  local mode=createComboBox(form)
  mode.Parent=form; mode.Left=210; mode.Top=174; mode.Width=740; mode.Style="csDropDownList"
  for _, item in ipairs(MODE_TEXT) do addComboItem(mode, item[S.language]) end
  label("variant", 218)
  local variant=createComboBox(form)
  variant.Parent=form; variant.Left=210; variant.Top=214; variant.Width=740; variant.Style="csDropDownList"
  label("customKey", 258)
  local customKey=createEdit(form)
  customKey.Parent=form; customKey.Left=210; customKey.Top=254; customKey.Width=500
  local customButton=createButton(form)
  customButton.Parent=form; customButton.Left=725; customButton.Top=252
  customButton.Width=225; customButton.Height=28; customButton.Caption=uiText("resolve")
  local summary=makeLabel(form, "", 18, 300, 932)
  summary.AutoSize=false; summary.Height=54; summary.WordWrap=true
  local applyButton=createButton(form)
  applyButton.Parent=form; applyButton.Left=210; applyButton.Top=360
  applyButton.Width=360; applyButton.Height=36; applyButton.Caption=uiText("apply")
  local restoreButton=createButton(form)
  restoreButton.Parent=form; restoreButton.Left=590; restoreButton.Top=360
  restoreButton.Width=360; restoreButton.Height=36; restoreButton.Caption=uiText("restore")
  local resetButton=createButton(form)
  resetButton.Parent=form; resetButton.Left=210; resetButton.Top=406
  resetButton.Width=500; resetButton.Height=32; resetButton.Caption=uiText("reset")
  local logButton=createButton(form)
  logButton.Parent=form; logButton.Left=725; logButton.Top=406
  logButton.Width=225; logButton.Height=32; logButton.Caption=uiText("log")
  local note=makeLabel(form, uiText("note"), 18, 454, 932)
  note.AutoSize=false; note.Height=58; note.WordWrap=true
  local safety=makeLabel(form, uiText("safety"), 18, 520, 932)
  safety.AutoSize=false; safety.Height=58; safety.WordWrap=true
  local status=makeLabel(form, uiText("ready"), 18, 590, 932)
  status.AutoSize=false; status.Height=72; status.WordWrap=true

  S.form=form
  S.controls={ source=source, include=include, catalog=catalog, character=character,
    search=search, mode=mode, variant=variant, customKey=customKey,
    summary=summary, status=status }

  source.OnChange=function()
    if S.uiLoading then return end
    saveEditorState()
    loadEditorState((tonumber(source.ItemIndex) or 0) == 1 and "kiryu" or "ichiban")
  end
  include.OnChange=saveEditorState
  catalog.OnChange=function()
    if S.uiLoading then return end
    local state=currentSlotState(); state.catalogIndex=tonumber(catalog.ItemIndex) or 0
    refreshTargetListV12(state.targetId); saveEditorState()
  end
  search.OnChange=function()
    if S.uiLoading then return end
    local state=currentSlotState(); state.query=tostring(search.Text or "")
    refreshTargetListV12(state.targetId); saveEditorState()
  end
  character.OnChange=function()
    if S.uiLoading then return end
    local state=currentSlotState(); state.targetId=currentEditorTargetId()
    refreshVariantsV12(0); saveEditorState()
  end
  mode.OnChange=function()
    if S.uiLoading then return end
    local state=currentSlotState(); state.modeIndex=tonumber(mode.ItemIndex) or 0
    refreshVariantsV12(state.variantIndex); saveEditorState()
  end
  variant.OnChange=saveEditorState
  customButton.OnClick=function()
    local ok, result=S.prepareCustomTarget(customKey.Text)
    if not ok then updateStatus("ERROR: " .. tostring(result)); return end
    local state=currentSlotState()
    state.customTargetId=result.id; state.targetId=result.id; state.catalogIndex=3
    catalog.ItemIndex=3; refreshTargetListV12(result.id); saveEditorState()
  end
  languageButton.OnClick=function()
    saveEditorState()
    S.language = S.language == "zh" and "en" or "zh"
    S.form=nil; S.controls=nil
    pcall(function() form.destroy() end)
    S.showSelector()
  end
  applyButton.OnClick=function()
    saveEditorState()
    local slots={}
    for _, sourceId in ipairs(allSourceIds()) do
      local state=S.slotStates[sourceId]
      if state and state.include then
        slots[sourceId]={ include=true, targetId=state.targetId,
          mode=MODE_IDS[(state.modeIndex or 0)+1],
          variantIndex=(state.variantIndex or 0)+1 }
      end
    end
    local ok, err=S.applySlots(slots)
    if not ok then updateStatus("ERROR: " .. tostring(err)) end
  end
  restoreButton.OnClick=function()
    local ok, err=S.restore("v1.2 selector Restore button")
    if not ok then updateStatus("ERROR: " .. tostring(err)) end
  end
  resetButton.OnClick=function()
    local ok, err=S.forceResetToVanilla("v1.2 selector emergency reset")
    if not ok then updateStatus("ERROR: " .. tostring(err)) end
  end
  logButton.OnClick=function()
    if type(shellExecute) == "function" then pcall(shellExecute, LOG_PATH) end
    updateStatus((S.language == "zh" and "诊断日志：" or "Diagnostic log: ") .. LOG_PATH)
  end
  form.OnClose=function()
    saveEditorState(); S.form=nil; S.controls=nil
  end
  loadEditorState(S.editingSourceId or "ichiban")
  form.show()
  updateStatus("READY v" .. SCRIPT_VERSION .. "; independent Ichiban/Kiryu slots enabled")
  return true
end

local function monitorStatusOnce(key, message)
  if S.monitorLastMessage == key then return end
  S.monitorLastMessage = key
  updateStatus(message)
end

local function connectionTick()
  if S.monitorBusy then return end
  S.monitorBusy = true
  local okTick, tickError = pcall(function()
    local pid = currentPid()

    if not pid then
      if S.monitorPid or S.pid or S.characterDb or S.costumeDb or S.backup then
        clearDeadProcessState(S.monitorPid or S.pid, "game process ended")
      end
      S.monitorRetryTicks = 0
      monitorStatusOnce("waiting",
        "WAITING / 等待游戏：start likeadragon8.exe; it will be attached automatically")
      return
    end

    if (S.monitorPid and S.monitorPid ~= pid) or (S.pid and S.pid ~= pid) then
      clearDeadProcessState(S.monitorPid or S.pid,
        "new likeadragon8.exe process detected")
    end
    S.monitorPid = pid

    if S.monitorValidatedPid == pid and S.characterDb and S.costumeDb then
      return
    end
    if S.monitorRetryTicks > 0 then
      S.monitorRetryTicks = S.monitorRetryTicks - 1
      return
    end

    monitorStatusOnce("scanning_" .. tostring(pid),
      "CONNECTING / 正在连接：game found; validating runtime databases...")
    local okValidate, validateError = S.validateAll()
    if okValidate then
      S.monitorValidatedPid = pid
      S.monitorRetryTicks = 0
      monitorStatusOnce("ready_" .. tostring(pid),
        "READY / 已连接：runtime databases verified; choose a character and Apply")
    else
      -- Loading screens and early startup may not have both databases yet.
      -- Retry after ten seconds without treating this expected state as fatal.
      S.monitorValidatedPid = nil
      S.characterDb = nil
      S.costumeDb = nil
      S.monitorRetryTicks = 4
      monitorStatusOnce("loading_" .. tostring(pid) .. "_" .. tostring(validateError),
        "WAITING / 等待数据库：" .. tostring(validateError) .. "; retrying automatically")
    end
  end)
  S.monitorBusy = false
  if not okTick then
    appendLog("MONITOR_ERROR " .. tostring(tickError))
    monitorStatusOnce("monitor_error_" .. tostring(tickError),
      "ERROR / 自动连接错误：" .. tostring(tickError))
  end
end

local function startConnectionMonitor()
  if type(createTimer) ~= "function" then
    updateStatus("WARNING / 警告：this CE build has no timer support; attach manually")
    return false
  end
  local timer = createTimer(nil, false)
  if not timer then
    updateStatus("WARNING / 警告：could not create automatic process monitor")
    return false
  end
  timer.Interval = 2000
  timer.OnTimer = connectionTick
  timer.Enabled = true
  S.connectionTimer = timer
  connectionTick()
  return true
end

updateStatus("v" .. SCRIPT_VERSION .. " loaded | recommended=" ..
  tostring(#(PLAN.targetOrder or {})) .. " | advanced female NPCs=" ..
  tostring(#(PLAN.labTargetOrder or {})) .. " | male NPCs=" ..
  tostring(#(PLAN.maleTargetOrder or {})) .. " | auto-connect enabled")
startConnectionMonitor()
