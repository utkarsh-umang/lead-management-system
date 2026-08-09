/**
 * Bound Google Apps Script for an Instascraper workbook.
 *
 * In the source spreadsheet, open Extensions > Apps Script, paste this file,
 * save, and run exportInstascraperToCsv. The script validates every non-empty
 * tab, adds Google Place ID and Scrape City, and creates one CSV in My Drive.
 * It never edits the source workbook and deliberately preserves duplicate rows;
 * LMS deduplicates them by Google Place ID while retaining raw provenance.
 */

const INSTASCRAPER_SOURCE_HEADERS = [
  "Maps Link",
  "Business Name",
  "Phone",
  "Business Type",
  "Website",
  "Rating",
  "Address",
  "Address 2",
  "Timings",
  "Reviews",
];

const INSTASCRAPER_OUTPUT_HEADERS = [
  "Google Place ID",
  "Scrape City",
  ...INSTASCRAPER_SOURCE_HEADERS,
];

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("Instascraper")
    .addItem("Export all tabs to LMS CSV", "exportInstascraperToCsv")
    .addToUi();
}

function exportInstascraperToCsv() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const outputRows = [INSTASCRAPER_OUTPUT_HEADERS];
  let sourceRows = 0;
  let exportedTabs = 0;

  spreadsheet.getSheets().forEach((sheet) => {
    const values = sheet.getDataRange().getDisplayValues();
    if (values.length === 0 || values.every((row) => isEmptyRow_(row))) {
      return;
    }

    const actualHeaders = values[0].map((value) => String(value).trim());
    validateHeaders_(sheet.getName(), actualHeaders);
    exportedTabs += 1;

    values.slice(1).forEach((sourceRow, index) => {
      if (isEmptyRow_(sourceRow)) {
        return;
      }

      const normalizedRow = INSTASCRAPER_SOURCE_HEADERS.map((_, columnIndex) =>
        columnIndex < sourceRow.length ? sourceRow[columnIndex] : ""
      );
      const mapsUrl = String(normalizedRow[0]).trim();
      const placeId = extractGooglePlaceId_(mapsUrl);
      if (!placeId) {
        throw new Error(
          `Missing Google Place ID in ${sheet.getName()} row ${index + 2}: ${mapsUrl}`
        );
      }

      outputRows.push([placeId, sheet.getName(), ...normalizedRow]);
      sourceRows += 1;
    });
  });

  if (sourceRows === 0) {
    throw new Error("No Instascraper data rows were found.");
  }

  const csv = outputRows.map((row) => row.map(csvCell_).join(",")).join("\r\n");
  const timezone = spreadsheet.getSpreadsheetTimeZone() || Session.getScriptTimeZone();
  const timestamp = Utilities.formatDate(new Date(), timezone, "yyyyMMdd-HHmmss");
  const filename = `instascraper-google-maps-${timestamp}.csv`;
  const file = DriveApp.createFile(Utilities.newBlob(csv, "text/csv", filename));
  const message =
    `Created ${filename}\n` +
    `${sourceRows} rows from ${exportedTabs} tabs\n` +
    file.getUrl();

  console.log(message);
  SpreadsheetApp.getUi().alert("Instascraper export complete", message, SpreadsheetApp.getUi().ButtonSet.OK);
}

function validateHeaders_(sheetName, actualHeaders) {
  const expected = JSON.stringify(INSTASCRAPER_SOURCE_HEADERS);
  const actual = JSON.stringify(actualHeaders);
  if (actual !== expected) {
    throw new Error(
      `Unexpected headers in ${sheetName}.\nExpected: ${expected}\nActual: ${actual}`
    );
  }
}

function extractGooglePlaceId_(mapsUrl) {
  const match = String(mapsUrl).match(/!19s([^?&]+)/);
  if (!match) {
    return "";
  }
  try {
    return decodeURIComponent(match[1]);
  } catch (_error) {
    return match[1];
  }
}

function isEmptyRow_(row) {
  return row.every((value) => String(value).trim() === "");
}

function csvCell_(value) {
  return `"${String(value == null ? "" : value).replace(/"/g, '""')}"`;
}
