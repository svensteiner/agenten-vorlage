$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
function Await($operation, [type]$resultType) {
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -like 'IAsyncOperation*' } | Select-Object -First 1
    $task = $method.MakeGenericMethod($resultType).Invoke($null, @($operation))
    return $task.GetAwaiter().GetResult()
}
$request = [Console]::In.ReadToEnd() | ConvertFrom-Json
$bytes = [Convert]::FromBase64String([string]$request.content_base64)
$stream = [Windows.Storage.Streams.InMemoryRandomAccessStream,Windows,ContentType=WindowsRuntime]::new()
$writer = [Windows.Storage.Streams.DataWriter,Windows,ContentType=WindowsRuntime]::new($stream)
$writer.WriteBytes($bytes)
Await ($writer.StoreAsync()) ([uint32]) | Out-Null
$writer.DetachStream() | Out-Null
$stream.Seek(0)
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder,Windows,ContentType=WindowsRuntime]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder,Windows,ContentType=WindowsRuntime])
$codec = ([guid]$decoder.DecoderInformation.CodecId).ToString().ToLowerInvariant()
$pngCodec = ([guid][Windows.Graphics.Imaging.BitmapDecoder,Windows,ContentType=WindowsRuntime]::PngDecoderId).ToString().ToLowerInvariant()
$jpegCodec = ([guid][Windows.Graphics.Imaging.BitmapDecoder,Windows,ContentType=WindowsRuntime]::JpegDecoderId).ToString().ToLowerInvariant()
if (($request.name -match '\.png$' -and $codec -ne $pngCodec) -or (($request.name -match '\.(jpg|jpeg)$') -and $codec -ne $jpegCodec)) { throw 'Image codec does not match extension.' }
if ($decoder.FrameCount -ne 1) { throw 'Animated or multi-frame images are not supported.' }
if ($decoder.PixelWidth -gt 4096 -or $decoder.PixelHeight -gt 4096 -or ($decoder.PixelWidth * $decoder.PixelHeight) -gt 8000000) { throw 'Image dimensions exceed OCR limit.' }
$bitmap = Await $decoder.GetSoftwareBitmapAsync() ([Windows.Graphics.Imaging.SoftwareBitmap,Windows,ContentType=WindowsRuntime])
$languages = [Windows.Media.Ocr.OcrEngine,Windows,ContentType=WindowsRuntime]::AvailableRecognizerLanguages
$language = $languages | Where-Object { $_.LanguageTag -eq 'de-DE' } | Select-Object -First 1
if ($null -eq $language) { $language = $languages | Where-Object { $_.LanguageTag -eq 'en-US' } | Select-Object -First 1 }
if ($null -eq $language) { throw 'No supported Windows OCR language is installed.' }
$engine = [Windows.Media.Ocr.OcrEngine,Windows,ContentType=WindowsRuntime]::TryCreateFromLanguage($language)
if ($null -eq $engine) { throw 'No Windows OCR language is installed.' }
$result = Await $engine.RecognizeAsync($bitmap) ([Windows.Media.Ocr.OcrResult,Windows,ContentType=WindowsRuntime])
$text = [string]$result.Text
if ([string]::IsNullOrWhiteSpace($text) -or $text.Length -gt 48000 -or $text.IndexOf([char]0) -ge 0) { throw 'OCR text is empty or exceeds limit.' }
@{ text = $text; extraction_method = 'windows-ocr'; language = [string]$language.LanguageTag } | ConvertTo-Json -Compress
