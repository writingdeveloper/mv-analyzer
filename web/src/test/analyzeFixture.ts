import fixture from '../../e2e/fixtures/analyze-report.json'
export function testReport() {
  const report=structuredClone(fixture)
  report.video.title='Example MV'
  report.video.video_id='abcdefghijk'
  report.benchmark.target_in_reference=false
  report.neighbors[0].title='Neighbor MV'
  return report
}
