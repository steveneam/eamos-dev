import { expect, test } from '@playwright/test'

test.setTimeout(60_000)

test('gnomAD map regions and ancestry rows highlight together', async ({ page }) => {
  await page.goto('/report?demo')

  const map = page.getByRole('img', {
    name: 'World map of gnomAD genetic ancestry group allele frequencies',
  })
  await expect(map).toBeVisible()
  await expect(page.locator('[data-gnomad-row="nfe"]')).toHaveCount(0)

  await page.getByRole('button', { name: 'Genetic ancestry group frequencies' }).click()

  const nfeRegion = page.locator('[data-gnomad-region="nfe"]')
  const nfeRow = page.locator('[data-gnomad-row="nfe"]')
  await nfeRegion.hover()
  await expect(nfeRow).toHaveCSS('border-color', 'rgb(253, 224, 71)')
  await expect(nfeRegion.locator('path')).toHaveAttribute('data-active', 'true')

  const afrRegion = page.locator('[data-gnomad-region="afr"]')
  const afrRow = page.locator('[data-gnomad-row="afr"]')
  await afrRow.hover()
  await expect(afrRow).toHaveCSS('border-color', 'rgb(253, 224, 71)')
  await expect(afrRegion.locator('path')).toHaveAttribute('data-active', 'true')
})
