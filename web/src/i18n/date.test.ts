import { expect, test, vi } from 'vitest'
import { formatDateValue, readSavedLocale, saveLocale } from './LocaleProvider'

test('calendar dates preserve the written day instead of being converted from UTC',()=>{
  expect(formatDateValue('2026-07-16','en')).toBe('Jul 16, 2026')
  expect(formatDateValue('20260716','en')).toBe('Jul 16, 2026')
  expect(formatDateValue('2026-07-16','ko')).toContain('16')
})


test('blocked storage leaves locale controls usable',()=>{
  const read=vi.spyOn(Storage.prototype,'getItem').mockImplementation(()=>{throw new DOMException('Storage blocked','SecurityError')})
  const write=vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new DOMException('Storage blocked','SecurityError')})
  try{
    expect(readSavedLocale()).toBeNull()
    expect(()=>saveLocale('en')).not.toThrow()
  }finally{read.mockRestore();write.mockRestore()}
})
