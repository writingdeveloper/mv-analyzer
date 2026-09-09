declare const validate: ((data: unknown) => boolean) & {
  errors?: Array<{instancePath:string;keyword:string;params:Record<string,unknown>;message?:string}> | null
}
export default validate
