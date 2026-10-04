# Actualiza la tabla de contenido y los campos del docx con Word y exporta el PDF.
param([Parameter(Mandatory=$true)][string]$Docx)
$ruta = (Resolve-Path -LiteralPath $Docx).Path
$pdf = [System.IO.Path]::ChangeExtension($ruta, '.pdf')
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($ruta, $false, $false)
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $doc.Fields.Update() | Out-Null
    $doc.Save()
    $doc.SaveAs([ref]$pdf, [ref]17)
    "paginas: " + $doc.ComputeStatistics(2)
    $doc.Close([ref]$false)
    "PDF: $pdf"
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
